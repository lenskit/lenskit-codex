"""
Batch inference code. Eventually this will probably move into LensKit.
"""

# pyright: basic
from __future__ import annotations

import gc
import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import ipyparallel as ipp
import numpy as np
import pandas as pd
from lenskit.algorithms import Recommender
from lenskit.algorithms.basic import TopN
from lenskit.sharing import PersistedModel
from lenskit.util import Stopwatch

_log = logging.getLogger(__name__)
__model: Recommender | None
__options: JobOptions | None


@dataclass
class UserResult:
    user: int
    wall_time: float

    test: pd.DataFrame
    recommendations: pd.DataFrame
    predictions: pd.DataFrame | None = None


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
    cluster: ipp.Cluster | ipp.Client | None = None,
) -> Iterator[UserResult]:
    with connect_cluster(cluster) as client:
        dv = client.direct_view()
        _log.info("sending model to workers")
        dv.apply_sync(_prepare_model, algo, JobOptions(n_recs, predict))
        try:
            _log.info("running recommender for %d users (N=%d)", test["user"].nunique(), n_recs)
            lbv = client.load_balanced_view()
            jobs = test.groupby("user")
            for res in lbv.imap(_run_for_user, jobs, ordered=False):
                yield res
        finally:
            _log.info("cleaning up model in workers")
            dv.apply_sync(_cleanup_model)


@contextmanager
def connect_cluster(cluster: ipp.Cluster | ipp.Client | None = None) -> Generator[ipp.Client]:
    if isinstance(cluster, ipp.Client):
        yield cluster
        return

    count = os.environ.get("LK_NUM_PROCS", None)
    if count is not None:
        count = int(count)
    else:
        count = min(os.cpu_count(), 8)  # type: ignore

    if cluster is None:
        _log.info("starting cluster with %s workers", count)
        with ipp.Cluster(n=count) as client:
            yield client
    else:
        yield cluster.connect_client_sync()


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

    watch = Stopwatch()
    recs = __model.recommend(user, __options.n_recs)
    recs["rank"] = np.arange(0, len(recs), dtype=np.int16) + 1

    if __options.predict:
        assert isinstance(__model, TopN)
        preds = __model.predict_for_user(user, test["item"])
        preds = preds.to_frame("prediction").reset_index()
        preds = preds.join(test.set_index("item")["rating"], on="item", how="left")

    time = watch.elapsed()

    return UserResult(user, time, test, recs, preds)
