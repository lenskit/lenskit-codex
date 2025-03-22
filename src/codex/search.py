"""
Support for hyperparameter search.
"""

from __future__ import annotations

import ray
from lenskit.batch import BatchPipelineRunner, BatchResults
from lenskit.logging import Task, get_logger
from lenskit.logging.worker import send_task
from lenskit.metrics import NDCG, RBP, RMSE, RecipRank, RunAnalysis
from lenskit.splitting import TTSplit

from codex.models import ModelDef, load_model
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.training import train_task

_log = get_logger(__name__)


class SimplePointEval:
    """
    A simple hyperparameter point evaluator using non-iterative model training.
    """

    def __init__(self, name: str, n: int | None, split: ray.ObjectRef, data_info: DataModel):
        self.name = name
        self.list_length = n
        self.data = split
        self.data_info = data_info

    def __call__(self, config) -> dict[str, float]:
        mod_def = load_model(self.name)
        data = ray.get(self.data)

        pipe, task = train_task(mod_def, config, data.train, self.data_info)
        send_task(task)

        runner = BatchPipelineRunner(n_jobs=1)  # single-threaded inside tuning
        runner.recommend()
        if mod_def.is_predictor:
            runner.predict()

        with CodexTask(
            label=f"measure {mod_def.name}",
            tags=["recommend"],
            reset_hwm=True,
            subprocess=True,
            scorer=ScorerModel(name=mod_def.name, config=config),
            data=self.data_info,
        ) as test_task:
            results = runner.run(pipe, data.test)

        send_task(test_task)
        return measure(mod_def, results, data, task, test_task)


def measure(
    model: ModelDef, results: BatchResults, data: TTSplit, train_task: Task, test_task: Task
):
    log = _log.bind(model=model.name)
    log.info("measuring recommendation lists")
    recm = RunAnalysis()
    recm.add_metric(RBP())
    recm.add_metric(NDCG())
    recm.add_metric(RecipRank())
    rec_metrics = recm.measure(results.output("recommendations"), data.test)

    if model.is_predictor:
        log.info("measuring rating predictions")
        predm = RunAnalysis()
        predm.add_metric(RMSE())
        pred_metrics = predm.measure(results.output("predictions"), data.test)
        rec_metrics.merge_from(pred_metrics)

    df = rec_metrics.list_summary()

    metrics = df.loc[:, "mean"].to_dict()
    metrics["TrainTask"] = train_task.task_id
    metrics["TrainTime"] = train_task.duration
    metrics["TrainCPU"] = train_task.cpu_time
    metrics["TestTask"] = test_task.task_id
    metrics["TestTime"] = test_task.duration
    metrics["TestCPU"] = test_task.cpu_time
    return metrics
