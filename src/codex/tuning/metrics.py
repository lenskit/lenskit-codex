from __future__ import annotations

from lenskit.batch import BatchResults
from lenskit.logging import Task, get_logger
from lenskit.metrics import NDCG, RBP, RMSE, RecipRank, RunAnalysis
from lenskit.splitting import TTSplit

from codex.models import ModelDef

_log = get_logger(__name__)


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
    if train_task is not None:
        metrics["TrainTask"] = train_task.task_id
        metrics["TrainTime"] = train_task.duration
        metrics["TrainCPU"] = train_task.cpu_time
    if test_task is not None:
        metrics["TestTask"] = test_task.task_id
        metrics["TestTime"] = test_task.duration
        metrics["TestCPU"] = test_task.cpu_time
    return metrics
