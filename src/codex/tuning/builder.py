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
from pydantic import JsonValue
from ray.tune.search.hyperopt import HyperOptSearch
from ray.tune.search.optuna import OptunaSearch

from codex.models import ModelDef
from codex.random import int_seed, rng_seed
from codex.runlog import DataModel
from codex.splitting import load_split_set

from .iterative import IterativeEval
from .job import DEFAULT_MAX_EPOCHS, TuningJobData
from .reporting import ProgressReport, StatusCallback
from .simple import SimplePointEval
from .stopper import RelativePlateauStopper

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
    spec: dict[str, JsonValue]

    data_info: DataModel
    data: TTSplit

    def __init__(self, model, out_dir, list_length, sample_count, metric):
        self.model = model
        self.out_dir = out_dir
        self.list_length = list_length
        self.sample_count = sample_count
        self.metric = metric
        self.spec = {
            "model": model.name,
            "metric": metric,
            "mode": self.mode,
            "list_length": list_length,
            "sample_count": sample_count,
        }

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
        self.spec["dataset"] = self.data_info.dataset

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
            self.spec["harness"] = "iterative"
            self.spec["max_epochs"] = limit
            harness = ray.tune.with_parameters(IterativeEval, job=self.job)
        else:
            self.spec["harness"] = "simple"
            harness = SimplePointEval(self.job)

        paracfg = get_parallel_config()

        self.log.info(
            "setting up parallel tuner",
            cpus=paracfg.total_threads,
            job_limit=self.job_limit,
            num_samples=self.sample_count,
        )
        self.spec["job_limit"] = self.job_limit
        self.harness = ray.tune.with_resources(
            harness, {"CPU": self.model.tuning_cpus, "GPU": self.model.tuning_gpus}
        )

    def create_random_tuner(self) -> ray.tune.Tuner:
        searcher = ray.tune.search.BasicVariantGenerator(
            random_state=default_rng(self.random_seed.spawn(1)[0])
        )
        return self._create_tuner(searcher)

    def create_hyperopt_tuner(self) -> ray.tune.Tuner:
        searcher = HyperOptSearch(random_state_seed=int_seed(self.random_seed.spawn(1)[0]))
        return self._create_tuner(searcher)

    def create_optuna_tuner(self) -> ray.tune.Tuner:
        searcher = OptunaSearch(seed=int_seed(self.random_seed.spawn(1)[0]))
        return self._create_tuner(searcher)

    def _create_tuner(self, searcher) -> ray.tune.Tuner:
        ray_store = self.out_dir / "state"
        scheduler = None
        stopper = None
        if self.model.is_iterative:
            min_iter = self.model.options.get("min_epochs", 5)
            self.spec["min_epochs"] = min_iter
            assert isinstance(min_iter, int)
            scheduler = ray.tune.schedulers.MedianStoppingRule(
                time_attr="training_iteration",
                grace_period=min_iter,
                min_time_slice=3,
                min_samples_required=5,
            )
            self.spec["scheduler"] = "median-stopping"
            stopper = RelativePlateauStopper(
                metric=self.metric,
                mode=self.mode,
                grace_period=min_iter,
                check_iters=min(min_iter, 3),
                min_improvement=0.005,
            )
            self.spec["stopper"] = {
                "type": "plateau",
                "num_results": 3,
                "min_improvement": 0.005,
            }
        self.spec["searcher"] = "random"
        if self.data.train.interaction_count >= 10_000_000:
            cp_freq = 2
        elif self.data.train.interaction_count >= 1_000_000:
            cp_freq = 3
        else:
            cp_freq = 5
        self.log.info("will checkpoint every %d iterations", cp_freq)
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
                progress_reporter=ProgressReport(self.model.name),
                failure_config=ray.tune.FailureConfig(fail_fast=True),
                callbacks=[StatusCallback(self.model.name, self.data_info.dataset)],
                stop=stopper,
                checkpoint_config=ray.tune.CheckpointConfig(
                    checkpoint_frequency=cp_freq,
                    num_to_keep=2,
                    # we don't need final model checkpoints
                    checkpoint_at_end=False,
                ),
            ),
        )
        return self.tuner
