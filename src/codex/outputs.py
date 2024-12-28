"""
Outputs of recommendation runs and sweeps.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import IO, Literal

import structlog
import zstandard
from pydantic import BaseModel, JsonValue

_log = structlog.stdlib.get_logger(__name__)

type RunLog = Literal["run", "inference", "training"]


class RunOutput:
    path: Path
    _log: structlog.stdlib.BoundLogger

    def __init__(self, path: Path) -> None:
        self.path = path
        self._log = _log.bind(path=str(path))

    @property
    def training_log_path(self):
        return self.path / "training.json"

    @property
    def inference_log_path(self):
        return self.path / "inference.json"

    @property
    def run_log_path(self):
        return self.path / "runs.json"

    @property
    def user_metric_path(self):
        return self.path / "user-metrics.ndjson.zst"

    @property
    def predictions_hive_path(self):
        return self.path / "predictions"

    @property
    def recommendations_hive_path(self):
        return self.path / "recommendations"

    def initialize(self):
        """
        Initialize run output directory.
        """

        if self.path.exists():
            self._log.debug("removing output directory")
            shutil.rmtree(self.path)

        self._log.debug("ensuring output directory exists")
        self.path.mkdir(exist_ok=True, parents=True)

    def user_metric_collector(self) -> NDJSONCollector:
        self._log.debug("opening metric output")
        return NDJSONCollector(self.user_metric_path)

    def record_log(self, rec_type: RunLog, data: dict[str, JsonValue] | BaseModel):
        """
        Record a log entry.
        """
        path: Path = getattr(self, f"{rec_type}_log_path")
        if isinstance(data, BaseModel):
            out_data = data.model_dump_json()
        else:
            out_data = json.dumps(data)

        with path.open("wt") as jsf:
            print(out_data, file=jsf)

    def __str__(self):
        return f"RunOutput({self.path})"


class NDJSONCollector:
    """
    Collect objects into an NDJSON file, with optional zstd compression.
    """

    path: Path
    fields: dict[str, JsonValue]
    output: IO[str]

    def __init__(self, path: Path, fields: dict[str, JsonValue] | None = None, **options):
        self.path = path
        self.fields = fields or {}

        path.parent.mkdir(exist_ok=True, parents=True)
        if path.suffix == ".zst":
            self.output = zstandard.open(path, "wt", zstandard.ZstdCompressor(**options))
        else:
            self.output = path.open("wt")

    def write_object(self, data: dict[str, JsonValue]):
        """
        Write the specified line to the output file.
        """
        print(json.dumps(self.fields | data), file=self.output)

    def close(self):
        self.output.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
