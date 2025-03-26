"""
Simple (non-iterative) evaluation of points.
"""

from __future__ import annotations

from lenskit.batch import BatchPipelineRunner
from lenskit.logging import get_logger
from lenskit.logging.worker import send_task
from pydantic_core import to_json

from codex.models import load_model
from codex.random import extend_seed
from codex.runlog import CodexTask, ScorerModel
from codex.training import train_task
from codex.tuning.job import TuningJobData

from .metrics import measure

_log = get_logger(__name__)


class SimplePointEval:
    """
    A simple hyperparameter point evaluator using non-iterative model training.
    """

    job: TuningJobData

    def __init__(self, job: TuningJobData):
        self.job = job

    def __call__(self, config) -> dict[str, float]:
        mod_def = load_model(self.job.model_name)
        factory = self.job.factory
        data = self.job.data

        rng = extend_seed(self.job.random_seed, to_json(config))
        pipe, task = train_task(
            mod_def, config, data.train, self.job.data_info, factory=factory, rng=rng
        )
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
            data=self.job.data_info,
        ) as test_task:
            results = runner.run(pipe, data.test)

        send_task(test_task)
        return measure(mod_def, results, data, task, test_task)
