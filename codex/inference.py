"""
Batch inference code. Eventually this will probably move into LensKit.
"""

# pyright: basic
from __future__ import annotations

import gc
import logging
from collections.abc import Generator
from dataclasses import dataclass
from typing import Iterator

import ipyparallel as ipp
import numpy as np
import pandas as pd
from lenskit.algorithms import Recommender
from lenskit.algorithms.basic import TopN
from lenskit.metrics.predict import mae, rmse
from lenskit.metrics.topn import ndcg, recip_rank
from lenskit.sharing import PersistedModel
from progress_api import Progress, make_progress

from codex.cluster import connect_cluster
from codex.resources import resource_monitor
from codex.results import UserResult

_log = logging.getLogger(__name__)
__model: Recommender | None
__options: JobOptions | None


@dataclass
class JobOptions:
    n_recs: int
    predict: bool


def run_recommender(
    algo: PersistedModel,
    test: pd.DataFrame,
    n_recs: int,
    predict: bool = False,
    *,
    cluster: ipp.Cluster | ipp.Client | None | bool = None,
) -> Iterator[UserResult]:
    global __model, __options
    if cluster == False:  # noqa: E712
        __model = algo.get()
        __options = JobOptions(n_recs, predict)
        for job in test.groupby("user"):
            yield _run_for_user(job)  # type: ignore
        return

    elif cluster == True:  # noqa: E712
        cluster = None

    with connect_cluster(cluster) as client:
        dv = client.direct_view()
        _log.info("sending model to workers")
        dv.apply_sync(_prepare_model, algo, JobOptions(n_recs, predict))
        try:
            n_users = test["user"].nunique()
            _log.info("running recommender for %d users (N=%d)", n_users, n_recs)
            lbv = client.load_balanced_view()
            with make_progress(
                _log, "generate", total=n_users, unit="user", states=["finished", "dispatched"]
            ) as pb:
                for res in lbv.imap(_run_for_user, _test_jobs(test, pb), ordered=False):
                    pb.update(state="finished", src_state="dispatched")
                    yield res
        finally:
            _log.info("cleaning up model in workers")
            dv.apply_sync(_cleanup_model)


def _test_jobs(test: pd.DataFrame, pb: Progress) -> Generator[tuple[int, pd.DataFrame]]:
    for group in test.groupby("user"):
        pb.update(state="dispatched")
        yield group  # type: ignore


def _prepare_model(model: PersistedModel, options: JobOptions):
    global __model, __options
    __model = model.get()
    __options = options


def _cleanup_model():
    global __model, __options
    __model = None
    __options = None
    gc.collect()


def _run_for_user(job: tuple[int, pd.DataFrame]):
    global __model, __options
    assert __model is not None
    assert __options is not None

    user, test = job
    test = test.set_index("item")

    with resource_monitor() as mon:
        result = UserResult(user, test)

        recs = __model.recommend(user, __options.n_recs)
        recs["rank"] = np.arange(0, len(recs), dtype=np.int16) + 1

        if len(recs) > 0:
            result.recommendations = recs
            result.metrics["ndcg"] = ndcg(recs, test.drop(columns="rating", errors="ignore"))
            result.metrics["recip_rank"] = recip_rank(recs, test)

        if __options.predict:
            assert isinstance(__model, TopN)
            preds = __model.predict_for_user(user, test.index.values)
            preds.index.name = "item"
            preds = preds.to_frame("prediction").reset_index()
            preds = preds.join(test["rating"], on="item", how="left")
            result.predictions = preds
            result.metrics["rmse"] = rmse(preds["prediction"], preds["rating"])
            result.metrics["mae"] = mae(preds["prediction"], preds["rating"])

    result.resources = mon.metrics()

    return result
