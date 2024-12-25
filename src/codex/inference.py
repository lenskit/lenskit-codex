"""
Batch inference code. Eventually this will probably move into LensKit.
"""

# pyright: basic
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import ray
import structlog
from lenskit import Pipeline, predict, recommend
from lenskit.data import ItemList, ItemListCollection, UserIDKey
from lenskit.logging import item_progress
from lenskit.logging.worker import WorkerLogConfig
from lenskit.metrics import MAE, NDCG, RBP, RMSE, Hit, RecipRank, RunAnalysisResult, call_metric
from lenskit.parallel.config import ParallelConfig, subprocess_config
from pyarrow.parquet import ParquetWriter
from pydantic import JsonValue

from codex.cluster import CodexActor, worker_pool
from codex.collect import NDJSONCollector

_log = structlog.stdlib.get_logger(__name__)


def recommend_and_save(
    pipe: Pipeline,
    test: ItemListCollection[UserIDKey],
    n_recs: int,
    rec_output: Path,
    pred_output: Path | None,
    metric_collector: NDJSONCollector | None = None,
    meta: dict[str, JsonValue] | None = None,
) -> RunAnalysisResult:
    if meta is None:
        meta = {}

    metric_list = []

    n_users = len(test)
    _log.info("running recommender for %d users (N=%d)", n_users, n_recs)
    if n_users < 500:
        runner = InferenceRunner(pipe, n_recs, rec_output, pred_output)
        with item_progress("generate", n_users) as pb:
            for user, data in test:
                metrics = runner.run_pipeline(user, data)
                metric_list.append(metrics)
                if metric_collector is not None:
                    metric_collector.write_object(meta | metrics)  # type: ignore
                pb.update()
    else:
        _log.info("sending pipeline to cluster")
        pipe_h = ray.put(pipe)
        del pipe
        with (
            worker_pool(
                InferenceActor,  # type: ignore
                subprocess_config(),
                WorkerLogConfig.current(),
                pipe_h,
                n_recs,
                rec_output,
                pred_output,
            ) as pool,
        ):
            with item_progress("generate", n_users) as pb:
                for metrics in pool.map_unordered(_call_actor, test._lists):
                    metric_list.append(metrics)
                    if metric_collector is not None:
                        metric_collector.write_object(meta | metrics)  # type: ignore
                    pb.update()

    df = pd.DataFrame.from_records(metric_list).set_index("user_id")
    return RunAnalysisResult(
        df,
        pd.Series(),
        defaults={
            "RBP": 0,
            "NDCG": 0,
            "RecipRank": 0,
            "Hit": 0,
        },
    )


def _call_actor(actor, query):
    return actor.run_pipeline.remote(*query)


class InferenceActor(CodexActor):
    runner: InferenceRunner

    def __init__(
        self,
        parallel: ParallelConfig,
        logging: WorkerLogConfig,
        pipeline: Pipeline,
        n: int | None,
        rec_output: Path,
        pred_output: Path | None,
    ):
        super().__init__(parallel, logging)
        self.runner = InferenceRunner(pipeline, n, rec_output, pred_output)

    def run_pipeline(self, key: UserIDKey, test: ItemList):
        return self.runner.run_pipeline(key, test)

    def finish(self):
        self.runner.finish()
        return super().finish()


class InferenceRunner:
    REC_FIELDS = {"item_id": pa.int32(), "rank": pa.int32(), "score": pa.float32()}
    PRED_FIELDS = {"item_id": pa.int32(), "score": pa.float32()}

    pipeline: Pipeline
    n_recs: int | None
    predict: bool
    rec_writer: ParquetWriter
    pred_writer: ParquetWriter | None = None

    rec_batch: ItemListCollection[UserIDKey]
    pred_batch: ItemListCollection[UserIDKey]

    def __init__(
        self,
        pipeline: Pipeline,
        n: int | None,
        rec_output: Path,
        pred_output: Path | None,
    ):
        assert isinstance(pipeline, Pipeline)
        self.pipeline = pipeline
        self.n_recs = n

        work_id = ray.get_runtime_context().get_worker_id()

        fn = f"worker-{work_id}.parquet"
        _log.debug("opening recommendation output", file=rec_output / fn)
        rec_output.mkdir(parents=True, exist_ok=True)
        self.rec_writer = ParquetWriter(
            rec_output / fn,
            pa.schema({"user_id": pa.int64(), "items": pa.list_(pa.struct(self.REC_FIELDS))}),
            compression="zstd",
            compression_level=6,
        )
        if pred_output is not None:
            _log.debug("opening prediction output", file=pred_output / fn)
            pred_output.mkdir(parents=True, exist_ok=True)
            self.pred_writer = ParquetWriter(
                pred_output / fn,
                pa.schema({"user_id": pa.int64(), "items": pa.list_(pa.struct(self.PRED_FIELDS))}),
                compression="zstd",
                compression_level=6,
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

        metrics: dict[str, JsonValue] = {"user_id": user}  # type: ignore
        metrics["RBP"] = float(call_metric(RBP, recs, test))
        metrics["NDCG"] = float(call_metric(NDCG, recs, test))
        metrics["RecipRank"] = float(call_metric(RecipRank, recs, test))
        metrics["Hit"] = float(call_metric(Hit, recs, test))

        if self.pred_writer is not None:
            preds = predict(self.pipeline, user, test)
            self.pred_batch.add(preds, *key)
            metrics["RMSE"] = float(call_metric(RMSE, preds, test))
            metrics["MAE"] = float(call_metric(MAE, preds, test))

        if len(self.rec_batch) >= 5000:
            self._write_batch()

        return metrics

    def finish(self):
        if len(self.rec_batch):
            self._write_batch()

        self.rec_writer.close()
        if self.pred_writer is not None:
            self.pred_writer.close()

    def _write_batch(self):
        _log.info("writing output batch", size=len(self.rec_batch))
        for rb in self.rec_batch._iter_record_batches(5000, self.REC_FIELDS):
            self.rec_writer.write_batch(rb)
        if self.pred_writer is not None:
            for rb in self.pred_batch._iter_record_batches(5000, self.PRED_FIELDS):
                self.pred_writer.write_batch(rb)

        self.rec_batch = ItemListCollection(UserIDKey)
        self.pred_batch = ItemListCollection(UserIDKey)
