"""
Outputs of recommendation runs and sweeps.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import IO, Literal

import pyarrow as pa
import structlog
import zstandard
from lenskit.data import ID, ItemList, ItemListCollection, UserIDKey
from pyarrow.parquet import ParquetDataset, ParquetWriter, write_table
from pydantic import BaseModel, JsonValue

_log = structlog.stdlib.get_logger(__name__)

type RunLog = Literal["run", "inference", "training"]
type ListSet = Literal["recommendations", "predictions"]

REC_FIELDS = {"item_id": pa.int32(), "rank": pa.int32(), "score": pa.float32()}
PRED_FIELDS = {"item_id": pa.int32(), "score": pa.float32()}


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

    @property
    def predictions_path(self):
        return self.path / "predictions.parquet"

    @property
    def recommendations_path(self):
        return self.path / "recommendations.parquet"

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

    def repack_output_lists(self):
        """
        Repack lit output from hives to flat Parquet files.
        """
        if self.recommendations_hive_path.exists():
            self._repack(
                "recommendations", self.recommendations_hive_path, self.recommendations_path
            )
        if self.predictions_hive_path.exists():
            self._repack("predictions", self.predictions_hive_path, self.predictions_path)

    def _repack(self, name: str, hive: Path, flat: Path):
        self._log.info("repacking hive", output=name)
        ds = ParquetDataset(hive)
        tbl = ds.read()
        write_table(tbl, flat, compression="zstd")
        self._log.debug("removing hive", output=name)
        shutil.rmtree(hive)

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


class ItemListCollector:
    """
    Collect item lists into a Parquet file.  Can be used as a Ray actor.
    """

    path: Path
    batch_size: int
    batch: ItemListCollection[UserIDKey]
    writer: ParquetWriter
    key_fields: list[str]
    list_fields: dict[str, pa.DataType]

    def __init__(
        self,
        path: Path,
        key_fields: dict[str, pa.DataType],
        list_fields: dict[str, pa.DataType],
        batch_size: int = 5000,
    ):
        self.path = path
        self.batch_size = batch_size
        self.key_fields = list(key_fields.keys())
        self.list_fields = list_fields

        self.batch = ItemListCollection(self.key_fields)
        fields = key_fields | {"items": pa.list_(pa.struct(list_fields))}
        self.writer = ParquetWriter(
            self.path,
            pa.schema(fields),
            compression="snappy",
        )

    def write_list(self, list: ItemList, *key: ID, **kw: ID):
        self.batch.add(list, *key, **kw)
        if len(self.batch) >= self.batch_size:
            self._write_batch()

    def finish(self):
        self._write_batch()
        self.writer.close()

    def _write_batch(self):
        if len(self.batch):
            for rb in self.batch._iter_record_batches(self.batch_size, self.list_fields):
                self.writer.write_batch(rb)
            self.batch = ItemListCollection(self.key_fields)
