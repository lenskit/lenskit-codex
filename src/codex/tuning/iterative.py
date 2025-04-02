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
from lenskit.pipeline import Component
from lenskit.training import ModelTrainer, TrainingOptions, UsesTrainer
from pydantic_core import to_json
from structlog.stdlib import BoundLogger

from codex.models import load_model
from codex.pipeline import base_pipeline, replace_scorer
from codex.random import extend_seed
from codex.runlog import CodexTask, ScorerModel

from .job import TuningJobData
from .metrics import measure

_log = get_logger(__name__)


def iterative_training_evaluator(job: TuningJobData):
    """
    Construct an iterative-training point evaluator.
    """

    class IterativeEval(ray.tune.Trainable):
        """
        A simple hyperparameter point evaluator using non-iterative model training.
        """

        job: TuningJobData
        log: BoundLogger
        task: CodexTask
        trainer: ModelTrainer
        epochs_trained: int

        def __init__(self):
            self.job = job

        def setup(self, config):
            self.mod_def = load_model(self.job.model_name)
            factory = self.job.factory
            self.data = self.job.data
            self.log = _log.bind(model=self.job.model_name, dataset=self.job.data_name)

            self.task = CodexTask(
                label=f"tune {self.mod_def.name}",
                tags=["tuning"],
                reset_hwm=True,
                subprocess=True,
                scorer=ScorerModel(name=self.mod_def.name, config=config),
                data=self.job.data_info,
            )

            self.log.info("configuring scorer", config=config)
            self.scorer = self.mod_def.instantiate(
                config | {"epochs": self.job.epoch_limit}, factory
            )
            assert isinstance(self.scorer, Component)
            assert isinstance(self.scorer, UsesTrainer)
            pipe = base_pipeline(self.job.model_name, predicts_ratings=self.mod_def.is_predictor)

            self.log.info("pre-training pipeline")
            pipe.train(self.data.train)
            self.pipe = replace_scorer(pipe, self.scorer)
            send_task(self.task)

            self.log.info("creating model trainer", config=self.scorer.config)
            options = TrainingOptions(
                rng=extend_seed(self.job.random_seed, to_json(self.scorer.dump_config()))
            )
            self.trainer = self.scorer.create_trainer(self.data.train, options)
            send_task(self.task)

            self.runner = BatchPipelineRunner(n_jobs=1)  # single-threaded inside tuning
            self.runner.recommend()
            if self.mod_def.is_predictor:
                self.runner.predict()

        def step(self):
            epoch = self.epochs_trained + 1
            elog = self.log.bind(epoch=epoch)

            vals = self.trainer.train_epoch()
            elog.debug("training iteration finished", result=vals)

            elog.debug("generating recommendations", n_queries=len(self.data.test))
            results = self.runner.run(self.pipe, self.data.test)

            elog.debug("measuring iteration results")
            metrics = measure(self.mod_def, results, self.data, self.task, None)
            metrics["max_epochs"] = self.job.epoch_limit
            send_task(self.task)
            elog.info("epoch complete")
            return metrics

        def cleanup(self):
            self.trainer.finalize()

    return IterativeEval
