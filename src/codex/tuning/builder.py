import os
from pathlib import Path

import numpy as np
import ray.tune
import ray.tune.schedulers
import ray.tune.search
import ray.tune.stopper
from lenskit.logging import get_logger
from lenskit.parallel import get_parallel_config
from lenskit.splitting import TTSplit
from lenskit.training import Trainable, TrainingOptions
from matplotlib.pylab import default_rng

from codex.models import ModelDef
from codex.random import rng_seed
from codex.runlog import DataModel
from codex.splitting import load_split_set

from .iterative import IterativeEval
from .job import DEFAULT_MAX_EPOCHS, TuningJobData
from .reporting import ProgressReport, StatusCallback
from .simple import SimplePointEval

_log = get_logger(__name__)


class TuningBuilder:
    """
    Builder for tuning jobs.
    """

    model: ModelDef
    out_dir: Path
    list_length: int
    sample_count: int
    job_limit: int | None
    metric: str
    random_seed: np.random.SeedSequence

    data_info: DataModel
    data: TTSplit

    def __init__(self, model, out_dir, list_length, sample_count, metric):
        self.model = model
        self.out_dir = out_dir
        self.list_length = list_length
        self.sample_count = sample_count
        self.metric = metric

        self.job_limit = int(os.environ.get("TUNING_JOB_LIMIT", "8"))
        if self.job_limit <= 0:
            self.job_limit = None

        self.log = _log.bind(model=model.name)
        self.random_seed = rng_seed("sweep", self.model.name)

    @property
    def mode(self):
        if self.metric == "RMSE":
            return "min"
        else:
            return "max"

    def load_data(self, split: Path, test_part: str, ds_name: str | None = None):
        self.log = self.log.bind(dataset=ds_name, split=split.stem)

        self.data = load_split_set(split).get_part(test_part)
        self.data_info = DataModel(
            dataset=ds_name or self.data.train.name,
            split=split.stem,
            part=test_part,
        )

    def prepare_factory(self):
        self.factory = self.model.tuning_factory()
        if isinstance(self.factory, Trainable):
            self.log.info("pre-training base model")
            self.factory.train(self.data.train, TrainingOptions())

    def setup_harness(self):
        self.log.info("setting up test harness")

        limit = self.model.options.get("max_epochs", DEFAULT_MAX_EPOCHS)
        assert isinstance(limit, int)
        self.job = TuningJobData(
            model_name=self.model.name,
            list_length=self.list_length,
            random_seed=self.random_seed.spawn(1)[0],
            epoch_limit=limit,
            data_info=self.data_info,
            factory_ref=ray.put(self.factory),
            data_ref=ray.put(self.data),
        )

        if self.model.is_iterative:
            harness = IterativeEval(self.job)
        else:
            harness = SimplePointEval(self.job)

        paracfg = get_parallel_config()

        self.log.info(
            "setting up parallel tuner",
            cpus=paracfg.total_threads,
            job_limit=self.job_limit,
            num_samples=self.sample_count,
        )
        self.harness = ray.tune.with_resources(
            harness, {"CPU": self.model.tuning_cpus, "GPU": self.model.tuning_gpus}
        )

    def create_random_tuner(self):
        ray_store = self.out_dir / "state"
        scheduler = None
        stopper = None
        if self.model.is_iterative:
            min_iter = self.model.options.get("min_epochs", 5)
            # max_epochs = self.model.options.get("max_epochs", DEFAULT_MAX_EPOCHS)
            assert isinstance(min_iter, int)
            # scheduler = ray.tune.schedulers.AsyncHyperBandScheduler(
            #     max_t=max_epochs,
            #     grace_period=min_iter,
            #     reduction_factor=2,
            # )
            scheduler = ray.tune.schedulers.MedianStoppingRule(
                grace_period=min_iter,
            )
            stopper = ray.tune.stopper.TrialPlateauStopper(
                self.metric, grace_period=min_iter, num_results=5
            )
        searcher = ray.tune.search.BasicVariantGenerator(
            random_state=default_rng(self.random_seed.spawn(1)[0])
        )
        self.tuner = ray.tune.Tuner(
            self.harness,
            param_space=self.model.search_space,
            tune_config=ray.tune.TuneConfig(
                metric=self.metric,
                mode=self.mode,
                num_samples=self.sample_count,
                max_concurrent_trials=self.job_limit,
                search_alg=searcher,
                scheduler=scheduler,
            ),
            run_config=ray.tune.RunConfig(
                storage_path=ray_store.absolute().as_uri(),
                verbose=None,
                progress_reporter=ProgressReport(),
                failure_config=ray.tune.FailureConfig(fail_fast=True),
                callbacks=[StatusCallback(self.model.name, self.data_info.dataset)],
                stop=stopper,
            ),
        )
        return self.tuner
