"""
Implementation of the log of all runs.
"""

from __future__ import annotations

import os
import socket
import tomllib
from pathlib import Path

import lenskit
import requests
import structlog
from deepmerge import always_merger
from humanize import metric
from lenskit.logging import Task
from pydantic import BaseModel, Field, JsonValue
from pyprojroot import find_root, has_file
from typing_extensions import override

_log = structlog.stdlib.get_logger(__name__)
_config: RunlogConfig | None = None

CONFIGS = ["config.toml", "local.toml"]


def configure():
    global _config
    if _config is not None:
        _log.warn("already configured")

    root = find_root(has_file("pixi.toml"))
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


class PrometheusConfig(BaseModel):
    url: str
    """
    URL to Prometheus instance.
    """

    queries: dict[str, str] = Field(default_factory=dict)


class CodexTask(Task):
    """
    Extended task with additional codex-specific logging information.
    """

    hostname: str = Field(default_factory=socket.gethostname)
    machine_name: str | None = Field(default_factory=lambda: os.environ.get("LK_MACHINE", None))
    lenskit_version: str = lenskit.__version__  # type: ignore
    tags: list[str] = Field(default_factory=list)

    model: str | None = None
    model_config: str | dict[str, JsonValue] | None = None

    cpu_power: float | None = None
    gpu_power: float | None = None
    chassis_power: float | None = None

    @override
    def start(self):
        if self._save_file is None and self.parent_id is None:
            cfg = get_config()
            self.save_to_file(cfg.lobby_dir / f"{self.task_id}.json", monitor=False)

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


def _get_prometheus_metric(url: str, query: str, time_ms: int) -> float | None:
    query = query.format(time_ms)
    log = _log.bind(url=url, query=query)
    try:
        res = requests.get(url, {"query": query}).json()
    except Exception as e:
        _log.warning("Prometheus query error", url=url, exception=e)
        return None

    log.debug("received response: %s", res)
    if res["status"] == "error":
        log.error("Prometheus query error: %s", res["error"], type=res["errorType"])
        return None

    results = res["data"]["result"]
    if len(results) != 1:
        log.warning("Prometheus query must return exactly 1 result, got %d", len(results))
        return None

    _time, val = results[0]["value"]
    return float(val)


def human_power(joules: float | None) -> str:
    if joules is None:
        return "NA"
    else:
        wh = joules / 3600
        return metric(wh, "Wh")
