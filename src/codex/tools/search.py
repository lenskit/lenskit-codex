"""
Hyperparameter search.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import click
import ray
import ray.train
import ray.tune
from lenskit.logging import get_logger
from lenskit.parallel import get_parallel_config

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
@click.option("-N", "--sample-count", type=int, metavar="N", default=100, help="test N points")
@click.option("--split", "split", type=Path, help="path to the split spec (or base file)")
@click.option("-N", "--ds-name", help="name of the dataset to split")
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

    ensure_cluster_init()

    harness = SimplePointEval(mod_def.name, list_length, data, data_info)
    paracfg = get_parallel_config()

    log.info("setting up parallel tuner", cpus=paracfg.total_threads)
    harness = ray.tune.with_resources(harness, {"CPU": paracfg.threads, "train-slots": 1})

    match method:
        case "random":
            scheduler = None
        case _:
            raise RuntimeError("no valid method specified")

    tuner = ray.tune.Tuner(
        harness,
        param_space=mod_def.search_space,
        tune_config=ray.tune.TuneConfig(
            metric=metric,
            mode="min" if metric == "RMSE" else "max",
            num_samples=sample_count,
            scheduler=scheduler,
        ),
        # run_config=ray.train.RunConfig(
        #     name=f"{mod_def.name}-{split.stem}", storage_path="./searches"
        # ),
    )

    log.info("starting hyperparameter search")
    results = tuner.fit()

    print(results)
