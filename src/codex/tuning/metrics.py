from __future__ import annotations

import numpy as np
import pandas as pd
from lenskit import Pipeline, predict, recommend
from lenskit.batch import BatchResults
from lenskit.data import ID, ItemList, ItemListCollection
from lenskit.logging import Task, get_logger
from lenskit.metrics import (
    DCG,
    NDCG,
    RBP,
    RMSE,
    Hit,
    ListMetric,
    RankingMetricBase,
    RecipRank,
    RunAnalysis,
    call_metric,
)
from lenskit.splitting import TTSplit
from pydantic import JsonValue
from scipy.special import logsumexp

from codex.models import ModelDef

_log = get_logger(__name__)


class LogRBP(ListMetric, RankingMetricBase):
    patience: float
    normalize: bool

    def __init__(self, k: int | None = None, *, patience: float = 0.85, normalize: bool = False):
        super().__init__(k)
        self.patience = patience
        self.normalize = normalize

    @property
    def label(self):
        if self.k is not None:
            return f"LogRBP@{self.k}"
        else:
            return "LogRBP"

    def measure_list(self, recs: ItemList, test: ItemList) -> float:
        recs = self.truncate(recs)
        k = len(recs)

        nrel = len(test)
        if nrel == 0:
            return np.nan

        items = recs.ids()
        good = np.isin(items, test.ids())
        # γ^(r-1)
        disc = np.arange(k) * np.log(self.patience)
        rbp = logsumexp(disc[good])
        return rbp - np.log(1 - self.patience)


def measure(
    model: ModelDef,
    results: BatchResults,
    data: TTSplit,
    train_task: Task | None = None,
    test_task: Task | None = None,
):
    log = _log.bind(model=model.name)
    log.debug("measuring recommendation lists")
    recm = RunAnalysis()
    recm.add_metric(RBP())
    recm.add_metric(LogRBP())
    recm.add_metric(NDCG())
    recm.add_metric(RecipRank())
    rec_metrics = recm.measure(results.output("recommendations"), data.test)

    if model.is_predictor:
        log.debug("measuring rating predictions")
        predm = RunAnalysis()
        predm.add_metric(RMSE())
        pred_metrics = predm.measure(results.output("predictions"), data.test)
        rec_metrics.merge_from(pred_metrics)

    df = rec_metrics.list_summary()

    metrics = df.loc[:, "mean"].to_dict()

    # compute LogRBP mean correctly
    lrbp = rec_metrics.list_metrics()["LogRBP"]
    metrics["LogRBP"] = logsumexp(lrbp) - np.log(len(lrbp))

    if train_task is not None:
        metrics["TrainTask"] = train_task.task_id
        metrics["TrainTime"] = train_task.duration
        metrics["TrainCPU"] = train_task.cpu_time
    if test_task is not None:
        metrics["TestTask"] = test_task.task_id
        metrics["TestTime"] = test_task.duration
        metrics["TestCPU"] = test_task.cpu_time
    return metrics


def measure_pipeline(
    model: ModelDef,
    pipe: Pipeline,
    test_users: ItemListCollection,
    train_task: Task | None = None,
    test_task: Task | None = None,
):
    metrics = [measure_user(model, pipe, key.user_id, test) for key, test in test_users.items()]
    metric_df = pd.DataFrame.from_records(metrics)
    metric_df = metric_df.drop(columns=["user_id"])
    agg_metrics = metric_df.mean().to_dict()

    if train_task is not None:
        agg_metrics["TrainTask"] = train_task.task_id
        agg_metrics["TrainTime"] = train_task.duration
        agg_metrics["TrainCPU"] = train_task.cpu_time
    if test_task is not None:
        test_task.update_resources()
        agg_metrics["TestTask"] = test_task.task_id
        agg_metrics["TestTime"] = test_task.duration
        agg_metrics["TestCPU"] = test_task.cpu_time
    return agg_metrics


def measure_user(model: ModelDef, pipe: Pipeline, user_id: ID, test: ItemList):
    recs = recommend(pipe, query=user_id)
    if model.is_predictor:
        preds = predict(pipe, query=user_id, items=test)
    else:
        preds = None
    return measure_list(model, user_id, recs, preds, test)


def measure_list(
    model: ModelDef,
    user_id: ID,
    recs: ItemList,
    preds: ItemList | None,
    test: ItemList,
):
    log = _log.bind(model=model.name, user_id=user_id)
    log.debug("measuring recommendation list")

    metrics: dict[str, JsonValue] = {"user_id": user_id}  # type: ignore
    metrics["RBP"] = float(call_metric(RBP, recs, test))
    metrics["DCG"] = float(call_metric(DCG, recs, test))
    metrics["NDCG"] = float(call_metric(NDCG, recs, test))
    metrics["RecipRank"] = float(call_metric(RecipRank, recs, test))
    metrics["Hit10"] = float(call_metric(Hit, recs, test, k=10))

    if preds is not None:
        log.debug("measuring rating predictions")
        metrics["RMSE"] = call_metric(RMSE, preds, test)

    return metrics
