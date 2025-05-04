"""
Hyperparameter search.
"""

from __future__ import annotations

import json
import os.path
import zipfile
from pathlib import Path
from typing import Literal

import click
import ray.tune.utils.log
from humanize import metric as human_metric
from humanize import precisedelta
from lenskit.logging import get_logger, stdout_console
from pydantic_core import to_json

from codex.cluster import ensure_cluster_init
from codex.models import load_model
from codex.runlog import CodexTask, ScorerModel
from codex.tuning import TuningBuilder

from . import codex

_log = get_logger(__name__)


@codex.command("search")
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
@click.option("--hyperopt", "method", flag_value="hyperopt", help="use HyperOpt search")
@click.option("--optuna", "method", flag_value="optuna", help="use Optuna search")
@click.option(
    "--metric",
    type=click.Choice(["RMSE", "LogRBP", "RBP", "RecipRank", "NDCG"]),
    default="RBP",
    help="Select the metric to optimize",
)
@click.argument("MODEL")
@click.argument("OUT", type=Path)
def run_search(
    model: str,
    out: Path,
    sample_count: int | None,
    split: Path,
    method: Literal["random", "hyperopt", "optuna"],
    metric: str,
    ds_name: str | None = None,
    test_part: str = "valid",
):
    console = stdout_console()
    log = _log.bind(model=model, dataset=ds_name, split=split.stem)
    mod_def = load_model(model)

    ray.tune.utils.log.set_verbosity(0)
    controller = TuningBuilder(mod_def, out, sample_count, metric)
    controller.load_data(split, test_part, ds_name)

    out.mkdir(exist_ok=True, parents=True)

    ensure_cluster_init()

    with (
        CodexTask(
            label=f"{method} search {model}",
            tags=["search", method],
            scorer=ScorerModel(name=model),
            data=controller.data_info,
        ) as task,
    ):
        controller.prepare_factory()
        controller.setup_harness()
        if method == "random":
            tuner = controller.create_random_tuner()
        elif method == "hyperopt":
            tuner = controller.create_hyperopt_tuner()
        elif method == "optuna":
            tuner = controller.create_optuna_tuner()
        else:
            raise ValueError(f"invalid method {method}")

        with open(out / "config.json", "wt") as jsf:
            print(to_json(controller.spec, indent=2).decode(), file=jsf)

        log.info("starting hyperparameter search")
        results = tuner.fit()

    fail = None
    if any(r.metrics is None or len(r.metrics) <= 1 for r in results):
        log.error("one or more runs did not complete")
        fail = RuntimeError("runs failed")

    best = results.get_best_result()
    fields = {metric: best.metrics[metric], "config": best.config}

    log.info("finished hyperparameter search", **fields)
    console.print("[bold yellow]Hyperparameter search completed![/bold yellow]")
    console.print("Best {} is [bold red]{:.3f}[/bold red]".format(metric, best.metrics[metric]))
    assert task.duration is not None
    line = "[bold magenta]{}[/bold magenta] trials took [bold cyan]{}[/bold cyan]".format(
        len(results),
        precisedelta(task.duration),  # type: ignore
    )
    if task.chassis_power:
        line += " and consumed [bold green]{}[/bold green]".format(
            human_metric(task.chassis_power / 3600, unit="Wh")
        )
    console.print(line)

    with open(out / "tuning-task.json", "wt") as jsf:
        print(task.model_dump_json(indent=2), file=jsf)

    with open(out / "trials.ndjson", "wt") as jsf:
        for result in results:
            print(to_json(result.metrics).decode(), file=jsf)

    best_out = best.metrics
    assert best_out is not None

    if mod_def.is_iterative:
        # see if we have an earlier, best configuration
        with open(os.path.join(best.path, "result.json"), "rt") as rjsf:
            iter_results = [json.loads(line) for line in rjsf]

        op = min if controller.mode == "min" else max
        best_out = op(iter_results, key=lambda r: r[metric]).copy()
        best_out["config"] = best_out["config"] | {"epochs": best_out["training_iteration"]}

        with open(out / "iterations.ndjson", "wt") as jsf:
            for n, result in enumerate(results):
                for i, row in result.metrics_dataframe.to_dict("index").items():
                    out_row = {"trial": n, "config": result.config}
                    out_row.update({k: v for (k, v) in row.items() if not k.startswith("config/")})
                    print(to_json(out_row).decode(), file=jsf)

    with open(out.with_suffix(".json"), "wt") as jsf:
        print(to_json(best_out).decode(), file=jsf)

    log.info("archiving search state")
    with zipfile.ZipFile(out / "tuning-state.zip", "w") as zipf:
        state_dir = out / "tuning-state"
        for dir, _sds, files in state_dir.walk():
            if dir.name.startswith("checkpoint_"):
                log.debug("skipping checkpoint directory")
                continue

            log.debug("adding directory", dir=dir)
            zipf.mkdir(dir.relative_to(out).as_posix())
            for file in files:
                fpath = dir / file
                fpstr = fpath.relative_to(out).as_posix()

                log.debug("adding file", file=fpstr)
                if fpath.suffix in [".gz", ".zst", ".pkl", ".pt"]:
                    comp = zipfile.ZIP_STORED
                else:
                    comp = zipfile.ZIP_DEFLATED

                zipf.write(fpath, fpstr, compress_type=comp)

    # log.debug("deleting unpacked search state")
    # shutil.rmtree(out / "state")

    if fail is not None:
        raise fail
