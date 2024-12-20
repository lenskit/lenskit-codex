"""
Batch inference code. Eventually this will probably move into LensKit.
"""

# pyright: basic
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterator

import ray
from lenskit import Pipeline, predict, recommend
from lenskit.data import ItemList, ItemListCollection, UserIDKey
from lenskit.logging import Task, item_progress
from lenskit.logging.worker import WorkerContext, WorkerLogConfig
from lenskit.metrics import MAE, NDCG, RBP, RMSE, RecipRank, call_metric
from lenskit.parallel.config import ParallelConfig, subprocess_config

from codex.cluster import CodexActor, create_pool
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
) -> Iterator[UserResult]:
    task = Task.current()
    if not ray.is_initialized():
        ray.init()
    _log.info("sending pipeline to cluster")
    pipe_h = ray.put(pipe)
    del pipe
    pool, workers = create_pool(
        InferenceActor, subprocess_config(), WorkerLogConfig.current(), pipe_h, n_recs, predict
    )
    try:
        n_users = len(test)
        _log.info("running recommender for %d users (N=%d)", n_users, n_recs)
        with item_progress("generate", n_users) as pb:
            for res in pool.map_unordered(_call_actor, test._lists):
                pb.update()
                yield ray.get(res)
    finally:
        for w in workers:
            st = ray.get(w.finish())
            if task is not None:
                task.add_subtask(st)


def _call_actor(actor, query):
    actor.run_pipeline(**query)


@ray.remote
class InferenceActor(CodexActor):
    pipeline: Pipeline
    n_recs: int | None
    predict: bool

    def __init__(
        self,
        parallel: ParallelConfig,
        logging: WorkerLogConfig,
        pipeline_ref: ray.ObjectRef,
        n: int | None,
        predict: bool,
    ):
        super().__init__(parallel, logging)
        self.pipeline = ray.get(pipeline_ref)
        self.n_recs = n
        self.predict = predict

    def run_pipeline(self, key: UserIDKey, test: ItemList):
        user = key.user_id

        start = time.perf_counter()

        result = UserResult(user, test)

        recs = recommend(self.pipeline, user, self.n_recs)
        result.recommendations = recs

        if len(recs) > 0:
            result.metrics["ndcg"] = call_metric(NDCG, recs, test)
            result.metrics["recip_rank"] = call_metric(RecipRank, recs, test)
            result.metrics["rbp"] = call_metric(RBP, recs, test, patience=0.8)

        if self.predict:
            preds = predict(self.pipeline, user, test)
            result.predictions = preds
            result.metrics["rmse"] = call_metric(RMSE, preds, test)
            result.metrics["mae"] = call_metric(MAE, preds, test)

        result.time = time.perf_counter() - start

        return result
