"""
Implementation of the log of all runs.
"""

from __future__ import annotations

import datetime as dt
import os
import socket
import subprocess as sp
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

import lenskit
import structlog
import zstandard
from lenskit.logging import Task
from pydantic import BaseModel, Field, JsonValue
from typing_extensions import override

from codex.config import get_config
from codex.layout import codex_root

_log = structlog.stdlib.get_logger(__name__)

CONFIGS = ["config.toml", "local.toml"]


def runlog_dir() -> Path:
    return codex_root() / "run-log"


def lobby_dir() -> Path:
    return runlog_dir() / "lobby"


def configure():
    lobby_dir().mkdir(exist_ok=True)


def machine_name() -> str:
    if name := os.environ.get("LK_MACHINE", None):
        return name
    else:
        cfg = get_config()
        if cfg.machine:
            return cfg.machine
        else:
            _log.warning("no machine name configured")
            return socket.gethostname()


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
    machine_name: str | None = Field(default_factory=machine_name)
    lenskit_version: str = lenskit.__version__  # type: ignore
    tags: list[str] = Field(default_factory=list)

    scorer: ScorerModel = Field(default_factory=ScorerModel)
    data: DataModel = Field(default_factory=DataModel)

    @override
    def start(self):
        if self._save_file is None and self.parent_id is None:
            self.save_to_file(lobby_dir() / f"{self.task_id}.json")

        super().start()


class RunLogDB:
    path: Path
    "The path to the run log."
    _open_files: dict[str, RunLogDBFile]
    "Cache of Runlog files that have been opened."

    def __init__(self):
        self.path = runlog_dir()
        self._open_files = {}

    @property
    def lobby_dir(self) -> Path:
        return self.path / "lobby"

    @property
    def db_dir(self) -> Path:
        return self.path / "db"

    def get_file(self, date: dt.date) -> RunLogDBFile:
        key = "{:4d}-{:02d}".format(date.year, date.month)
        dbf = self._open_files.get(key, None)
        if dbf is None:
            path = self.db_dir / f"{key}.ndjson.zst"
            if path.exists():
                dbf = RunLogDBFile.read_db(path)
            else:
                dbf = RunLogDBFile(path)
            self._open_files[key] = dbf

        return dbf

    def add_task(self, task: Task):
        if task.start_time is None:
            raise ValueError(f"task {task.task_id} has no start time")
        date = dt.datetime.fromtimestamp(task.start_time)
        dbf = self.get_file(date)
        dbf.add_task(task)

    def save_all(self):
        for dbf in self._open_files.values():
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
