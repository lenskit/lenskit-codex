"""
Batch inference code. Eventually this will probably move into LensKit.
"""

# pyright: basic
from __future__ import annotations

import asyncio
import math
import os
from dataclasses import dataclass
from itertools import batched
from pathlib import Path

import pandas as pd
import pyarrow as pa
import ray
from lenskit import Pipeline, predict, recommend
from lenskit.data import ID, ItemList, ItemListCollection, UserIDKey
from lenskit.logging import Task, get_logger, item_progress
from lenskit.logging.worker import send_task
from lenskit.metrics import MAE, NDCG, RBP, RMSE, Hit, RecipRank, RunAnalysisResult, call_metric
from pydantic import JsonValue

from codex.cluster import ensure_cluster_init
from codex.outputs import PRED_FIELDS, REC_FIELDS, DummySink, ItemListCollector, ObjectSink

_log = get_logger(__name__)


@dataclass
class PipelineResults:
    metrics: dict[str, JsonValue]
    recs: ItemList
    preds: ItemList | None = None


def recommend_and_save(
    pipe: Pipeline,
    test: ItemListCollection[UserIDKey],
    n_recs: int,
    rec_output: Path,
    pred_output: Path | None,
    metric_collector: ObjectSink | None = None,
    meta: dict[str, JsonValue] | None = None,
    prefer_async: bool = False,
) -> RunAnalysisResult:
    if metric_collector is None:
        metric_collector = DummySink()

    if meta is not None:
        metric_collector = metric_collector.with_fields(meta)

    metric_list = []

    n_users = len(test)
    log = _log.bind(n_users=n_users, n_recs=n_recs)

    if "LK_SEQUENTIAL" in os.environ or (n_users < 500 and not prefer_async):
        log.info("recommending in-process")

        collector = InferenceResultCollector(rec_output, pred_output)
        with item_progress("generate", n_users) as pb:
            for user, data in test:
                result = run_pipeline(pipe, user, data, n_recs)
                collector.write_output(result.recs, result.preds, user_id=user.user_id)
                metric_list.append(result.metrics)
                if metric_collector is not None:
                    metric_collector.write_object(result.metrics)
                pb.update()

        collector.finish()

    else:
        ensure_cluster_init()

        log.info("sending pipeline to cluster")
        pipe_h = ray.put(pipe)
        del pipe

        collector = ray.remote(InferenceResultCollector).remote(rec_output, pred_output)

        task = _run_batches_async(pipe_h, test, n_recs, collector, metric_collector)
        metric_list = asyncio.run(task)
        ray.get(collector.finish.remote())

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


async def _run_batches_async(pipe_h, test, n_recs: int, collector, metric_collector):
    n_users = len(test)
    # max of 64 batches
    batch_size = max(500, math.ceil(n_users / 64))

    log = _log.bind(n_users=n_users, n_recs=n_recs, batch_size=batch_size)
    log.info("launching asynchronous inference")

    tasks = []

    with item_progress("generate", n_users) as pb:
        async with asyncio.TaskGroup() as tg:
            for batch in batched(test, batch_size):
                task = _run_and_await_batch(pipe_h, batch, n_recs, pb, collector, metric_collector)
                tasks.append(tg.create_task(task))

    log.info("finished inference", n_batches=len(tasks))
    return [m for res in tasks for m in res.result()]


async def _run_and_await_batch(pipe_h, batch, n_recs, pb, collector, metric_collector):
    mlist = []
    async for metrics in run_pipeline_batch.remote(pipe_h, batch, n_recs, collector):
        metrics = ray.get(metrics)
        mlist.append(metrics)
        if metric_collector is not None:
            metric_collector.write_object(metrics)
        pb.update()

    return mlist


@ray.remote
def run_pipeline_batch(pipeline, batch, n_recs: int, collector):
    with Task("pipeline batch", reset_hwm=True, subprocess=True) as task:
        for user, data in batch:
            result = run_pipeline(pipeline, user, data, n_recs)
            t = collector.write_output.remote(result.recs, result.preds, user_id=user.user_id)
            ray.get(t)

            yield result.metrics

    send_task(task)


def run_pipeline(
    pipeline: Pipeline, key: UserIDKey, test: ItemList, n_recs: int
) -> PipelineResults:
    user = key.user_id

    recs = recommend(pipeline, user, n_recs)

    metrics: dict[str, JsonValue] = {"user_id": user}  # type: ignore
    metrics["RBP"] = float(call_metric(RBP, recs, test))
    metrics["NDCG"] = float(call_metric(NDCG, recs, test))
    metrics["RecipRank"] = float(call_metric(RecipRank, recs, test))
    metrics["Hit"] = float(call_metric(Hit, recs, test))

    result = PipelineResults(metrics, recs)

    rp = pipeline.node("rating-predictor", missing=None)
    if rp is not None:
        result.preds = predict(pipeline, user, test)
        metrics["RMSE"] = float(call_metric(RMSE, result.preds, test))
        metrics["MAE"] = float(call_metric(MAE, result.preds, test))

    return result


class InferenceResultCollector:
    """
    Collector for inference results.  Can run as a Ray actor.
    """

    rec_collector: ItemListCollector
    pred_collector: ItemListCollector | None = None

    def __init__(self, rec_output: Path, pred_output: Path | None):
        rec_output.parent.mkdir(parents=True, exist_ok=True)
        self.rec_collector = ItemListCollector(rec_output, {"user_id": pa.int64()}, REC_FIELDS)
        if pred_output is not None:
            pred_output.parent.mkdir(parents=True, exist_ok=True)
            self.pred_collector = ItemListCollector(
                pred_output, {"user_id": pa.int64()}, PRED_FIELDS
            )

    def write_output(self, recs: ItemList, preds: ItemList | None, **key: ID):
        self.rec_collector.write_list(recs, **key)
        if preds is not None and self.pred_collector is not None:
            self.pred_collector.write_list(preds, **key)

    def finish(self):
        self.rec_collector.finish()
        if self.pred_collector is not None:
            self.pred_collector.finish()
