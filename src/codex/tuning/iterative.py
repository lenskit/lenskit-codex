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

from codex.models import load_model
from codex.pipeline import base_pipeline, replace_scorer
from codex.runlog import CodexTask, DataModel, ScorerModel

from .metrics import measure

_log = get_logger(__name__)


class IterativeEval:
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
        epoch_limit: int,
    ):
        self.name = name
        self.factory_ref = factory
        self.list_length = n
        self.data_ref = split
        self.data_info = data_info
        self.epoch_limit = epoch_limit

    def __call__(self, config):
        mod_def = load_model(self.name)
        factory = ray.get(self.factory_ref)
        data = ray.get(self.data_ref)
        log = _log.bind(model=self.name, dataset=self.data_info.dataset)

        with CodexTask(
            label=f"tune {mod_def.name}",
            tags=["tuning"],
            reset_hwm=True,
            subprocess=True,
            scorer=ScorerModel(name=mod_def.name, config=config),
            data=self.data_info,
        ) as task:
            log.info("configuring scorer", config=config)
            model = factory(config | {"epochs": self.epoch_limit})
            assert isinstance(model, Component)
            assert isinstance(model, IterativeTraining)
            pipe = base_pipeline(self.name, predicts_ratings=mod_def.is_predictor)

            log.info("pre-training pipeline")
            pipe.train(data.train)
            pipe = replace_scorer(pipe, model)
            send_task(task)

            self.runner = BatchPipelineRunner(n_jobs=1)  # single-threaded inside tuning
            self.runner.recommend()
            if mod_def.is_predictor:
                self.runner.predict()

            log.info("starting training loop", config=model.config)
            training_loop = model.training_loop(data.train, TrainingOptions())
            send_task(task)
            log.info("beginning training epochs")
            for epoch, vals in enumerate(training_loop, 1):
                elog = log.bind(epoch=epoch)
                elog.debug("training iteration finished", result=vals)
                elog.debug("generating recommendations", n_queries=len(data.test))
                results = self.runner.run(pipe, data.test)

                elog.debug("measuring iteration results")
                metrics = measure(mod_def, results, data, task, None)
                send_task(task)
                ray.tune.report(metrics)
