"""
Simple (non-iterative) evaluation of points.
"""

from __future__ import annotations

import ray
import ray.tune
import ray.tune.result
from lenskit.batch import BatchPipelineRunner
from lenskit.logging import get_logger
from lenskit.logging.worker import send_task
from lenskit.training import IterativeTraining, TrainingOptions

from codex.models import load_model
from codex.pipeline import base_pipeline, replace_scorer
from codex.runlog import CodexTask, DataModel, ScorerModel

from .metrics import measure

_log = get_logger(__name__)


class IterativeEval(ray.tune.Trainable):
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
        self.factory_ref = factory
        self.list_length = n
        self.data_ref = split
        self.data_info = data_info

    def setup(self, config):
        self.mod_def = load_model(self.name)
        factory = ray.get(self.factory_ref)
        self.data = ray.get(self.data_ref)

        self.task = CodexTask(
            label=f"tune {self.mod_def.name}",
            tags=["tuning"],
            reset_hwm=True,
            subprocess=True,
            scorer=ScorerModel(name=self.mod_def.name, config=config),
            data=self.data_info,
        )
        _log.info("configuring scorer", model=self.name, config=config)
        self.model = factory(config)
        assert isinstance(self.model, IterativeTraining)
        self.pipe = base_pipeline(self.name, predicts_ratings=self.mod_def.is_predictor)

        _log.info("pre-training pipeline")
        self.data = ray.get(self.data_ref)
        self.pipe.train(self.data)

        self.runner = BatchPipelineRunner(n_jobs=1)  # single-threaded inside tuning
        self.runner.recommend()
        if self.mod_def.is_predictor:
            self.runner.predict()

        _log.info("starting training loop")
        self.training_loop = self.model.training_loop(self.data, TrainingOptions())
        send_task(self.task)

    def step(self):
        try:
            res = next(self.training_loop)
        except StopIteration:
            return ray.tune.result.DONE

        _log.debug("training iteration finished", result=res)
        pipe = replace_scorer(self.pipe, self.model)
        results = self.runner.run(pipe, self.data.test)

        _log.debug("measuring ireation results")
        metrics = measure(self.mod_def, results, self.data, self.task, None)
        send_task(self.task)
        return metrics

    def cleanup(self):
        _log.info("cleaning up search actor", model=self.model)
        del self.model
        del self.training_loop
        del self.pipe

        self.task.finish()
        send_task(self.task)
