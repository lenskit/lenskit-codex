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
from lenskit.training import IterativeTraining, TrainingOptions
from pydantic_core import to_json

from codex.models import load_model
from codex.pipeline import base_pipeline, replace_scorer
from codex.random import extend_seed
from codex.runlog import CodexTask, ScorerModel

from .job import TuningJobData
from .metrics import measure

_log = get_logger(__name__)


class IterativeEval:
    """
    A simple hyperparameter point evaluator using non-iterative model training.
    """

    job: TuningJobData

    def __init__(
        self,
        job: TuningJobData,
    ):
        self.job = job

    def __call__(self, config):
        mod_def = load_model(self.job.model_name)
        factory = self.job.factory
        data = self.job.data
        log = _log.bind(model=self.job.model_name, dataset=self.job.data_name)

        with CodexTask(
            label=f"tune {mod_def.name}",
            tags=["tuning"],
            reset_hwm=True,
            subprocess=True,
            scorer=ScorerModel(name=mod_def.name, config=config),
            data=self.job.data_info,
        ) as task:
            log.info("configuring scorer", config=config)
            model = mod_def.instantiate(config | {"epochs": self.job.epoch_limit}, factory)
            assert isinstance(model, Component)
            assert isinstance(model, IterativeTraining)
            pipe = base_pipeline(self.job.model_name, predicts_ratings=mod_def.is_predictor)

            log.info("pre-training pipeline")
            pipe.train(data.train)
            pipe = replace_scorer(pipe, model)
            send_task(task)

            self.runner = BatchPipelineRunner(n_jobs=1)  # single-threaded inside tuning
            self.runner.recommend()
            if mod_def.is_predictor:
                self.runner.predict()

            log.info("starting training loop", config=model.config)
            options = TrainingOptions(
                rng=extend_seed(self.job.random_seed, to_json(model.dump_config()))
            )
            training_loop = model.training_loop(data.train, options)
            send_task(task)
            log.info("beginning training epochs")
            for epoch, vals in enumerate(training_loop, 1):
                elog = log.bind(epoch=epoch)
                elog.debug("training iteration finished", result=vals)
                elog.debug("generating recommendations", n_queries=len(data.test))
                results = self.runner.run(pipe, data.test)

                elog.debug("measuring iteration results")
                metrics = measure(mod_def, results, data, task, None)
                metrics["max_epochs"] = self.job.epoch_limit
                send_task(task)
                elog.info("epoch complete")
                ray.tune.report(metrics)
