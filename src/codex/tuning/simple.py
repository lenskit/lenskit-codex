"""
Simple (non-iterative) evaluation of points.
"""

from __future__ import annotations

import ray
from lenskit.batch import BatchPipelineRunner
from lenskit.logging import get_logger
from lenskit.logging.worker import send_task

from codex.models import load_model
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.training import train_task

from .metrics import measure

_log = get_logger(__name__)


class SimplePointEval:
    """
    A simple hyperparameter point evaluator using non-iterative model training.
    """

    def __init__(
        self,
        name: str,
        factory: ray.ObjectRef,
        split: ray.ObjectRef,
        data_info: DataModel,
        n: int | None,
    ):
        self.name = name
        self.factory = factory
        self.list_length = n
        self.data = split
        self.data_info = data_info

    def __call__(self, config) -> dict[str, float]:
        mod_def = load_model(self.name)
        factory = ray.get(self.factory)
        data = ray.get(self.data)

        pipe, task = train_task(mod_def, config, data.train, self.data_info, factory=factory)
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
