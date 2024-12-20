"""
Batch inference code. Eventually this will probably move into LensKit.
"""

# pyright: basic
from __future__ import annotations

import logging
from pathlib import Path

import pyarrow as pa
import ray
from lenskit import Pipeline, predict, recommend
from lenskit.data import ItemList, ItemListCollection, UserIDKey
from lenskit.logging import item_progress
from lenskit.logging.worker import WorkerLogConfig
from lenskit.parallel.config import ParallelConfig, subprocess_config
from pyarrow.parquet import ParquetWriter

from codex.cluster import CodexActor, worker_pool
from codex.runlog import CodexTask

_log = logging.getLogger(__name__)


def recommend_and_save(
    pipe: Pipeline,
    test: ItemListCollection[UserIDKey],
    n_recs: int,
    rec_output: Path,
    pred_output: Path | None,
) -> CodexTask:
    if not ray.is_initialized():
        ray.init()
    _log.info("sending pipeline to cluster")
    name = pipe.name
    pipe_h = ray.put(pipe)
    del pipe
    with (
        CodexTask(f"recommend-{name}", tags=["generate"], reset_hwm=True) as task,
        worker_pool(
            InferenceActor,
            subprocess_config(),
            WorkerLogConfig.current(),
            pipe_h,
            n_recs,
            rec_output,
            pred_output,
        ) as pool,
    ):
        n_users = len(test)
        _log.info("running recommender for %d users (N=%d)", n_users, n_recs)
        with item_progress("generate", n_users) as pb:
            for _res in pool.map_unordered(_call_actor, test._lists):
                pb.update()

    return task


def _call_actor(actor, query):
    actor.run_pipeline(**query)


@ray.remote
class InferenceActor(CodexActor):
    REC_FIELDS = {"item_id": pa.int32, "rank": pa.int32, "score": pa.float32()}
    PRED_FIELDS = {"item_id": pa.int32, "score": pa.float32()}

    pipeline: Pipeline
    n_recs: int | None
    predict: bool
    rec_writer: ParquetWriter
    pred_writer: ParquetWriter | None = None

    rec_batch: ItemListCollection[UserIDKey]
    pred_batch: ItemListCollection[UserIDKey]

    def __init__(
        self,
        parallel: ParallelConfig,
        logging: WorkerLogConfig,
        pipeline_ref: ray.ObjectRef,
        n: int | None,
        rec_output: Path,
        pred_output: Path | None,
    ):
        super().__init__(parallel, logging)
        self.pipeline = ray.get(pipeline_ref)
        self.n_recs = n
        self.rec_writer = ParquetWriter(
            rec_output,
            pa.schema({"user_id": pa.int32, "items": pa.list_(pa.struct(self.REC_FIELDS))}),
        )
        if pred_output is not None:
            self.pred_writer = ParquetWriter(
                pred_output,
                pa.schema({"user_id": pa.int32, "items": pa.list_(pa.struct(self.PRED_FIELDS))}),
            )
        else:
            self.pred_writer = None

        self.rec_batch = ItemListCollection(UserIDKey)
        self.pred_batch = ItemListCollection(UserIDKey)

    def run_pipeline(self, key: UserIDKey, test: ItemList):
        user = key.user_id

        # start = time.perf_counter()

        recs = recommend(self.pipeline, user, self.n_recs)
        self.rec_batch.add(recs, *key)

        if self.pred_writer is not None:
            preds = predict(self.pipeline, user, test)
            self.pred_batch.add(preds, *key)

        if len(self.rec_batch) >= 5000:
            for rb in self.rec_batch._iter_record_batches(5000, self.REC_FIELDS):
                self.rec_writer.write_batch(rb)
            if self.pred_writer is not None:
                for rb in self.pred_batch._iter_record_batches(5000, self.PRED_FIELDS):
                    self.pred_writer.write_batch(rb)

    def finish(self):
        if len(self.rec_batch):
            for rb in self.rec_batch._iter_record_batches(5000, self.REC_FIELDS):
                self.rec_writer.write_batch(rb)
            if self.pred_writer is not None:
                for rb in self.pred_batch._iter_record_batches(5000, self.PRED_FIELDS):
                    self.pred_writer.write_batch(rb)

        super().finish()
