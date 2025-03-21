"""
Hyperparameter search.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import click
import ray
import ray.train
import ray.tune
from lenskit.logging import get_logger, item_progress
from lenskit.parallel import get_parallel_config
from pydantic_core import to_json

from codex.cluster import ensure_cluster_init
from codex.models import load_model
from codex.outputs import RunOutput
from codex.runlog import DataModel
from codex.search import SimplePointEval
from codex.splitting import load_split_set

from . import codex

_log = get_logger(__name__)


@codex.command("search")
@click.option(
    "-n", "--list-length", type=int, metavar="N", default=1000, help="generate lists of length N"
)
@click.option(
    "-C", "--sample-count", type=int, metavar="NPTS", default=100, help="test NPTS points"
)
@click.option("--split", "split", type=Path, help="path to the split spec (or base file)")
@click.option("-N", "--ds-name", help="name of the dataset to search with")
@click.option(
    "-p",
    "--test-part",
    default="valid",
    metavar="PART",
    help="validate on PART",
)
@click.option("--random", "method", flag_value="random", help="use random search")
@click.option(
    "--metric",
    type=click.Choice(["RMSE", "RBP", "RecipRank", "NDCG"]),
    default="RBP",
    help="Select the metric to optimize",
)
@click.argument("MODEL")
@click.argument("OUT", type=Path)
def run_sweep(
    model: str,
    out: Path,
    list_length: int,
    sample_count: int,
    split: Path,
    method: Literal["random"],
    metric: str,
    ds_name: str | None = None,
    test_part: str = "valid",
):
    log = _log.bind(model=model, dataset=ds_name, split=split.stem)
    mod_def = load_model(model)

    output = RunOutput(out)
    output.initialize()

    data_info = DataModel(dataset=ds_name, split=split.stem, part=test_part)
    split_set = load_split_set(split)
    data = split_set.get_part(test_part)
    # data.test = data.test.pack()

    ensure_cluster_init()

    log.info("pushing data to storage")
    data_ref = ray.put(data)
    harness = SimplePointEval(mod_def.name, list_length, data_ref, data_info)
    paracfg = get_parallel_config()

    if lktj := os.environ.get("TUNING_JOB_LIMIT", None):
        job_limit = int(lktj)
    else:
        job_limit = None

    log.info(
        "setting up parallel tuner",
        cpus=paracfg.total_threads,
        job_limit=job_limit,
        num_samples=sample_count,
    )
    harness = ray.tune.with_resources(harness, {"CPU": mod_def.tuning_cpus})

    match method:
        case "random":
            scheduler = None
        case _:
            raise RuntimeError("no valid method specified")

    ray_store = out / "state"
    tuner = ray.tune.Tuner(
        harness,
        param_space=mod_def.search_space,
        tune_config=ray.tune.TuneConfig(
            metric=metric,
            mode="min" if metric == "RMSE" else "max",
            num_samples=sample_count,
            scheduler=scheduler,
            max_concurrent_trials=job_limit,
        ),
        run_config=ray.train.RunConfig(
            storage_path=ray_store.absolute().as_uri(),
            verbose=None,
            progress_reporter=ProgressReport(),
            callbacks=[StatusCallback(mod_def.name, ds_name)],
        ),
    )

    log.info("starting hyperparameter search")
    results = tuner.fit()
    best = results.get_best_result()
    fields = {metric: best.metrics[metric]} | best.config
    log.info("finished hyperparameter search", **fields)

    with open(out / "trials.ndjson", "wt") as jsf:
        for result in results:
            print(to_json(result.metrics).decode(), file=jsf)
    with open(out / "best.json", "wt") as jsf:
        print(to_json(best.metrics).decode(), file=jsf)


class StatusCallback(ray.tune.Callback):
    def __init__(self, model: str, ds: str | None):
        self.log = _log.bind(model=model, dataset=ds)

    def on_trial_result(self, iteration, trials, trial, result, **info):
        metrics = {n: v for (n, v) in result.items() if n in ["RBP", "NDCG", "RecipRank", "RMSE"]}
        self.log.info("new trial result", iter=iteration, id=trial.trial_id, **metrics)


class ProgressReport(ray.tune.ProgressReporter):
    metric = None
    mode = None
    best_metric = None

    def __init__(self):
        super().__init__()
        self.done = set()

    def setup(self, start_time=None, total_samples=None, metric=None, mode=None, **kwargs):
        super().setup(start_time, total_samples, metric, mode, **kwargs)

        _log.info("setting up tuning status", total_samples=total_samples, metric=metric, mode=mode)
        extra = {metric: ".3f"} if metric is not None else {}
        self._bar = item_progress("Tuning trials", total_samples, extra)
        self.metric = metric
        self.mode = mode

    def report(self, trials, done, *sys_info):
        _log.debug("reporting trial completion", trial_count=len(trials))

        if done:
            _log.info("search complete", trial_count=len(trials))
            self._bar.finish()
        else:
            total = len(trials)
            if total < self._bar.total:
                total = None

            n_new = 0
            for trial in trials:
                if trial.status == "TERMINATED" and trial.trial_id not in self.done:
                    self.done.add(trial.trial_id)
                    n_new += 1
                    _log.debug("finished trial", id=trial.trial_id, config=trial.config)
                    if self.metric is not None:
                        mv = trial.last_result[self.metric]
                        if self.best_metric is None:
                            self.best_metric = mv
                        elif self.mode == "max" and mv > self.best_metric:
                            self.best_metric = mv
                        elif self.mode == "min" and mv < self.best_metric:
                            self.best_metric = mv

            extra = {}
            if self.best_metric is not None:
                extra = {self.metric: self.best_metric}
            self._bar.update(n_new, total=total, **extra)

    def should_report(self, trials, done=False):
        done = set(t.trial_id for t in trials if t.status == "TERMINATED")
        if done - self.done:
            return True
        else:
            return False
