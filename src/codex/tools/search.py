"""
Hyperparameter search.
"""

from __future__ import annotations

import shutil
import tarfile
from pathlib import Path
from typing import Literal

import click
import zstandard
from lenskit.logging import get_logger
from pydantic_core import to_json

from codex.cluster import ensure_cluster_init
from codex.models import load_model
from codex.runlog import CodexTask, ScorerModel
from codex.tuning import TuningController

from . import codex

_log = get_logger(__name__)


@codex.command("search")
@click.option(
    "-n", "--list-length", type=int, metavar="N", default=1000, help="generate lists of length N"
)
@click.option("-C", "--sample-count", type=int, metavar="N", help="test N points")
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
    sample_count: int | None,
    split: Path,
    method: Literal["random"],
    metric: str,
    ds_name: str | None = None,
    test_part: str = "valid",
):
    log = _log.bind(model=model, dataset=ds_name, split=split.stem)
    mod_def = load_model(model)
    if sample_count is None:
        sample_count = mod_def.options.get("search_points", 100)  # type: ignore

    controller = TuningController(mod_def, out, list_length, sample_count, metric)
    controller.load_data(split, test_part, ds_name)

    ensure_cluster_init()

    with (
        CodexTask(
            label=f"{method} search {model}",
            tags=["search"],
            scorer=ScorerModel(name=model),
            data=controller.data_info,
        ) as task,
    ):
        controller.prepare_factory()
        controller.setup_harness()
        tuner = controller.create_random_tuner()

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

    if mod_def.is_iterative:
        with open(out / "iterations.ndjson", "wt") as jsf:
            for n, result in enumerate(results):
                for i, row in result.metrics_dataframe.to_dict("index").items():
                    out_row = {"trial": n, "config": result.config, "epoch": i}
                    out_row.update({k: v for (k, v) in row.items() if not k.startswith("config/")})
                    print(to_json(out_row), file=jsf)

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
