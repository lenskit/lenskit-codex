from __future__ import annotations

import numpy as np
from lenskit.batch import BatchResults
from lenskit.data import ItemList
from lenskit.logging import Task, get_logger
from lenskit.metrics import NDCG, RBP, RMSE, ListMetric, RankingMetricBase, RecipRank, RunAnalysis
from lenskit.splitting import TTSplit
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
