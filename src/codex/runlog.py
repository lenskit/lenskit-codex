"""
Implementation of the log of all runs.
"""

from __future__ import annotations

import datetime as dt
import os
import socket
import subprocess as sp
import tomllib
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

import lenskit
import requests
import structlog
import zstandard
from deepmerge import always_merger
from humanize import metric
from lenskit.logging import Task
from pydantic import BaseModel, Field, JsonValue
from typing_extensions import override

from codex.layout import codex_root

_log = structlog.stdlib.get_logger(__name__)
_config: RunlogConfig | None = None

CONFIGS = ["config.toml", "local.toml"]


def configure():
    global _config
    if _config is not None:
        _log.warn("already configured")

    root = codex_root()
    rl_base = root / "run-log"
    log = _log.bind(root=rl_base)

    cfg = RunlogConfig(base_dir=rl_base).model_dump()
    for cfg_name in CONFIGS:
        cfile = rl_base / cfg_name
        if cfile.exists():
            log.debug("reading RL configuration", file=cfile)
            with cfile.open("rb") as f:
                contrib = tomllib.load(f)

            always_merger.merge(cfg, contrib)

    _config = RunlogConfig.model_validate(cfg)
    _config.lobby_dir.mkdir(exist_ok=True)


def get_config() -> RunlogConfig:
    if _config is None:
        configure()

    assert _config is not None
    return _config


class RunlogConfig(BaseModel):
    """
    Schema for runlog configuration file (``runlog/config.toml`` and ``runlog/local.toml``).
    """

    base_dir: Path
    prometheus: PrometheusConfig | None = None

    @property
    def lobby_dir(self):
        return self.base_dir / "lobby"

    @property
    def db_dir(self):
        return self.base_dir / "db"


class PrometheusConfig(BaseModel):
    url: str
    """
    URL to Prometheus instance.
    """

    queries: dict[str, str] = Field(default_factory=dict)


class DataModel(BaseModel):
    dataset: str | None = None
    split: str | None = None
    part: str | int | None = None


class ScorerModel(BaseModel):
    name: str | None = None
    config: dict[str, JsonValue] | None = None


class CodexTask(Task):
    """
    Extended task with additional codex-specific logging information.
    """

    hostname: str = Field(default_factory=socket.gethostname)
    machine_name: str | None = Field(default_factory=lambda: os.environ.get("LK_MACHINE", None))
    lenskit_version: str = lenskit.__version__  # type: ignore
    tags: list[str] = Field(default_factory=list)

    scorer: ScorerModel = Field(default_factory=ScorerModel)
    data: DataModel = Field(default_factory=DataModel)

    cpu_power: float | None = None
    "CPU power consumed in Joules."
    gpu_power: float | None = None
    "GPU power consumed in Joules."
    chassis_power: float | None = None
    "Chassis power consumed in Joules."

    @override
    def start(self):
        if self._save_file is None and self.parent_id is None:
            cfg = get_config()
            self.save_to_file(cfg.lobby_dir / f"{self.task_id}.json")

        super().start()

    @override
    def update_resources(self):
        res = super().update_resources()

        config = get_config()
        if prom := config.prometheus:
            url = config.prometheus.url + "/api/v1/query"
            assert self.duration is not None
            time_ms = int(self.duration * 1000)
            if "cpu_power" in prom.queries:
                self.cpu_power = _get_prometheus_metric(url, prom.queries["cpu_power"], time_ms)
            if "gpu_power" in prom.queries:
                self.gpu_power = _get_prometheus_metric(url, prom.queries["gpu_power"], time_ms)
            if "chassis_power" in prom.queries:
                self.chassis_power = _get_prometheus_metric(
                    url, prom.queries["chassis_power"], time_ms
                )

        return res


class RunLogDB:
    config: RunlogConfig
    open_files: dict[str, RunLogDBFile]

    def __init__(self):
        self.config = get_config()
        self.open_files = {}

    def get_file(self, date: dt.date) -> RunLogDBFile:
        key = "{:4d}-{:02d}".format(date.year, date.month)
        dbf = self.open_files.get(key, None)
        if dbf is None:
            path = self.config.db_dir / f"{key}.ndjson.zst"
            if path.exists():
                dbf = RunLogDBFile.read_db(path)
            else:
                dbf = RunLogDBFile(path)
            self.open_files[key] = dbf

        return dbf

    def save_all(self):
        for dbf in self.open_files.values():
            dbf.save_db()


class RunLogDBFile:
    """
    A single file of run log data (representing one month).

    Tasks are stored *flattened*: each subtask — except for subprocess subtasks
    — is a distinct entry, and its subtasks is empty (except for the subprocess
    subtasks).
    """

    path: Path
    log_entries: dict[UUID, Task]

    def __init__(self, path: Path, entries: Iterable[CodexTask] | None = None) -> None:
        self.path = path
        if entries is None:
            self.log_entries = {}
        else:
            self.log_entries = {t.task_id: t for t in entries}

    def add_task(self, task: Task):
        """
        Add a task and its subtasks to the codex run log.
        """
        log = _log.bind(task_id=task.task_id.hex)
        if task.task_id in self.log_entries:
            log.debug("task already in log, updating")
        else:
            log.debug("adding task to log")
        sp_tasks = [t for t in task.subtasks if t.subprocess]
        self.log_entries[task.task_id] = task.model_copy(update={"subtasks": sp_tasks})
        for t in task.subtasks:
            if not t.subprocess:
                self.add_task(t)

    def save_db(self, *, path: Path | None = None):
        if path is None:
            path = self.path
        log = _log.bind(file=path.as_posix(), n=len(self.log_entries))
        log.debug("sorting task entries")
        entries = sorted(self.log_entries.values(), key=lambda t: t.start_time or 0)
        log.info("saving task database")
        path.parent.mkdir(exist_ok=True, parents=True)
        pid = os.getpid()
        tmpfile = path.with_name(f"{path.name}.{pid}.tmp")
        with zstandard.open(tmpfile, "wt", zstandard.ZstdCompressor(level=6)) as outf:
            for e in entries:
                print(e.model_dump_json(), file=outf)
        os.rename(tmpfile, path)
        log.debug("adding DB file to DVC")
        sp.check_call(["dvc", "add", path])

    @classmethod
    def read_db(cls, path: Path) -> RunLogDBFile:
        log = _log.bind(file=path)
        log.debug("reading task database")
        with zstandard.open(path, "rt") as inf:
            db = cls(path, (CodexTask.model_validate_json(line) for line in inf))
            log.info("read task database", n=len(db.log_entries))
        return db


def power_metrics(name: str, duration: float):
    time_ms = int(duration * 1000)

    config = get_config()
    prom = config.prometheus
    if not prom:
        return None
    url = prom.url + "/api/v1/query"
    if name in prom.queries:
        return _get_prometheus_metric(url, prom.queries[name], time_ms)


def _get_prometheus_metric(url: str, query: str, time_ms: int) -> float | None:
    query = query.format(time_ms)
    log = _log.bind(url=url, query=query)
    try:
        res = requests.get(url, {"query": query}).json()
    except Exception as e:
        log.warning("Prometheus query error", exc_info=e)
        return None

    log.debug("received response: %s", res)
    if res["status"] == "error":
        log.error("Prometheus query error: %s", res["error"], type=res["errorType"])
        return None

    results = res["data"]["result"]
    if len(results) != 1:
        log.debug("Prometheus query must return exactly 1 result, got %d", len(results))
        return None

    _time, val = results[0]["value"]
    return float(val)


def human_power(joules: float | None) -> str:
    if joules is None:
        return "NA"
    else:
        wh = joules / 3600
        return metric(wh, "Wh")
