"""
Hyperparameter search.
"""

from __future__ import annotations

import os
import shutil
import tarfile
from pathlib import Path
from typing import Literal

import click
import ray
import ray.train
import ray.tune
import zstandard
from lenskit.logging import get_logger
from lenskit.parallel import get_parallel_config
from lenskit.training import Trainable, TrainingOptions
from pydantic_core import to_json

from codex.cluster import ensure_cluster_init
from codex.models import load_model
from codex.outputs import RunOutput
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.splitting import load_split_set
from codex.tuning.reporting import ProgressReport, StatusCallback
from codex.tuning.simple import SimplePointEval

from . import codex

_log = get_logger(__name__)


@codex.command("search")
@click.option(
    "-n", "--list-length", type=int, metavar="N", default=1000, help="generate lists of length N"
)
@click.option("-C", "--sample-count", type=int, metavar="N", default=100, help="test N points")
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
    data = load_split_set(split).get_part(test_part)
    # data.test = data.test.pack()

    ensure_cluster_init()

    with (
        CodexTask(
            label=f"{method} search {model}",
            tags=["search"],
            scorer=ScorerModel(name=model),
            data=data_info,
        ) as task,
    ):
        factory = mod_def.tuning_factory()
        if isinstance(factory, Trainable):
            log.info("pre-training base model")
            factory.train(data.train, TrainingOptions())

        log.info("pushing data to storage")
        data_ref = ray.put(data)
        del data
        fac_ref = ray.put(factory)
        del factory

        log.info("setting up test harness")
        harness = SimplePointEval(mod_def.name, fac_ref, list_length, data_ref, data_info)
        paracfg = get_parallel_config()

        job_limit = int(os.environ.get("TUNING_JOB_LIMIT", "8"))
        if job_limit <= 0:
            job_limit = None

        log.info(
            "setting up parallel tuner",
            cpus=paracfg.total_threads,
            job_limit=job_limit,
            num_samples=sample_count,
        )
        harness = ray.tune.with_resources(
            harness, {"CPU": mod_def.tuning_cpus, "GPU": mod_def.tuning_gpus}
        )

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
            run_config=ray.tune.RunConfig(
                storage_path=ray_store.absolute().as_uri(),
                verbose=None,
                progress_reporter=ProgressReport(),
                callbacks=[StatusCallback(mod_def.name, ds_name)],
            ),
        )

        log.info("starting hyperparameter search")
        results = tuner.fit()

    fail = None
    if any(r.metrics is None or len(r.metrics) <= 1 for r in results):
        log.error("one or more runs did not complete")
        fail = RuntimeError("runs failed")

    best = results.get_best_result()
    fields = {metric: best.metrics[metric]} | best.config

    log.info(
        "finished hyperparameter search", time=task.duration, power=task.chassis_power, **fields
    )

    with open(out / "tuning-task.json", "wt") as jsf:
        print(task.model_dump_json(indent=2), file=jsf)

    with open(out / "trials.ndjson", "wt") as jsf:
        for result in results:
            print(to_json(result.metrics).decode(), file=jsf)
    with open(out.with_suffix(".json"), "wt") as jsf:
        print(to_json(best.metrics).decode(), file=jsf)

    log.info("compressing search state")
    with (
        zstandard.open(out / "state.tar.zst", "wb") as zf,
        tarfile.TarFile(mode="w", fileobj=zf) as tar,
    ):
        tar.add(out / "state", "state")
    shutil.rmtree(out / "state")

    if fail is not None:
        raise fail
