"""
Batch inference code. Eventually this will probably move into LensKit.
"""

# pyright: basic
from __future__ import annotations

import gc
import logging
import time
from dataclasses import dataclass
from typing import Iterator

import ipyparallel as ipp
from lenskit import Pipeline, predict, recommend
from lenskit.data import ItemList, ItemListCollection, UserIDKey
from lenskit.logging import Task, item_progress
from lenskit.logging.worker import WorkerContext, WorkerLogConfig
from lenskit.metrics import MAE, NDCG, RBP, RMSE, RecipRank, call_metric
from lenskit.parallel.serialize import SHMData, shm_deserialize, shm_serialize

from codex.cluster import connect_cluster
from codex.results import UserResult

_log = logging.getLogger(__name__)
__pipeline: Pipeline | None
__options: JobOptions | None
__context: WorkerContext
__task: Task


@dataclass
class JobOptions:
    n_recs: int
    predict: bool


def run_recommender(
    pipe: Pipeline,
    test: ItemListCollection[UserIDKey],
    n_recs: int,
    predict: bool = False,
    *,
    cluster: ipp.Cluster | ipp.Client | None | bool = None,
) -> Iterator[UserResult]:
    global __pipeline, __options
    if cluster == False:  # noqa: E712
        __pipeline = pipe
        __options = JobOptions(n_recs, predict)
        for job in test:
            yield _run_for_user(job)
        return

    elif cluster == True:  # noqa: E712
        cluster = None

    with connect_cluster(cluster) as client:
        dv = client.direct_view()
        _log.info("sending model to workers")
        data = shm_serialize(pipe)
        dv.apply_sync(_prepare_model, data, JobOptions(n_recs, predict), WorkerLogConfig.current())
        try:
            n_users = len(test)
            _log.info("running recommender for %d users (N=%d)", n_users, n_recs)
            lbv = client.load_balanced_view()
            with item_progress("generate", n_users) as pb:
                for res in lbv.imap(_run_for_user, test, ordered=False):
                    pb.update(state="finished", src_state="dispatched")
                    yield res
        finally:
            _log.info("cleaning up model in workers")
            dv.apply_sync(_cleanup_model)


def _prepare_model(model: SHMData, options: JobOptions, logging: WorkerLogConfig):
    global __pipeline, __options, __task
    __context = WorkerContext(logging)
    __context.start()
    __pipeline = shm_deserialize(model)
    __options = options
    __task = Task("recommend worker", subprocess=True)
    __task.start()


def _cleanup_model():
    global __pipeline, __options, __task, __context
    __task.finish()
    __context.send_task(__task)
    del __task

    __pipeline = None
    __options = None

    __context.shutdown()
    del __context
    gc.collect()


def _run_for_user(job: tuple[UserIDKey, ItemList]):
    global __pipeline, __options
    assert __pipeline is not None
    assert __options is not None

    key, test = job
    user = key.user_id

    start = time.perf_counter()

    result = UserResult(user, test)

    recs = recommend(__pipeline, user, __options.n_recs)
    result.recommendations = recs

    if len(recs) > 0:
        result.metrics["ndcg"] = call_metric(NDCG, recs, test)
        result.metrics["recip_rank"] = call_metric(RecipRank, recs, test)
        result.metrics["rbp"] = call_metric(RBP, recs, test, patience=0.8)

    if __options.predict:
        preds = predict(__pipeline, user, test)
        result.predictions = preds
        result.metrics["rmse"] = call_metric(RMSE, preds, test)
        result.metrics["mae"] = call_metric(MAE, preds, test)

    result.time = time.perf_counter() - start

    return result
