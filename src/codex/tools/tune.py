"""
Hyperparameter search.
"""

from __future__ import annotations

import warnings
import zipfile
from pathlib import Path
from typing import Literal

import click
from humanize import metric as human_metric
from humanize import precisedelta
from lenskit.logging import get_logger, stdout_console
from lenskit.schemas.tuning import ErrorAction, TuningSpec
from lenskit.tuning import PipelineTuner
from pydantic_core import to_json

from codex.config import load_config
from codex.layout import model_dir
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.splitting import load_split_set

from . import codex

_log = get_logger(__name__)


@codex.command("tune")
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
@click.option("--ray", "use_ray", is_flag=True, help="use Ray Tune")
@click.option("--random", "method", flag_value="random", help="use random search")
@click.option("--hyperopt", "method", flag_value="hyperopt", help="use HyperOpt search")
@click.option("--tpe", "method", flag_value="tpe", help="use Optuna/TPE search")
@click.option(
    "--metric",
    type=click.Choice(["RMSE", "RBP", "RecipRank", "NDCG"]),
    help="Select the metric to optimize",
)
@click.option(
    "--on-error",
    type=click.Choice(["abort", "continue"], case_sensitive=False),
    default="continue",
    envvar="LK_TUNE_ON_ERROR",
    help="What to do when a trial fails.",
)
@click.argument("MODEL")
@click.argument("OUT", type=Path)
def run_tune(
    model: str,
    out: Path,
    sample_count: int | None,
    split: Path,
    use_ray: bool,
    method: Literal["random", "hyperopt", "optuna"] | None,
    on_error: ErrorAction,
    metric: str | None = None,
    ds_name: str | None = None,
    test_part: str = "valid",
):
    console = stdout_console()
    log = _log.bind(model=model, dataset=ds_name, split=split.stem)
    codex_cfg = load_config()

    warnings.filterwarnings("error", r".*global interpreter lock.*enabled.*", RuntimeWarning)

    spec = TuningSpec.load(model_dir(model) / "search.toml")
    if sample_count is not None:
        spec.search.default_points = sample_count
    else:
        spec.search.default_points = codex_cfg.tuning[method or "optuna"].points

    if method is not None:
        if not use_ray:
            _log.warn("search methods only supported with Ray Tune")
        spec.search.method = method

    if metric is not None:
        spec.search.metric = metric
    spec.search.update_max_points(sample_count)
    spec.search.error_action = on_error

    metric = spec.search.metric
    assert metric is not None

    if use_ray:
        import ray.tune.utils.log
        from lenskit.parallel.ray import ensure_cluster
        from lenskit.tuning import RayPipelineTuner

        ray.tune.utils.log.set_verbosity(0)
        ensure_cluster()
        tuner = RayPipelineTuner(spec, out_dir=out)
    else:
        tuner = PipelineTuner(spec, out_dir=out)

    splits = load_split_set(split)
    data = splits.get_part(test_part)
    tuner.set_data(data.train, data.test, name=data.name)
    data_model = DataModel(dataset=data.name or ds_name, split=split.stem, part=test_part)

    out.mkdir(exist_ok=True, parents=True)

    with (
        CodexTask(
            label=f"{method} search {model}",
            tags=["search", method or "optuna"],
            scorer=ScorerModel(name=model),
            data=data_model,
        ) as task,
    ):
        with open(out / "config.json", "wt") as jsf:
            print(tuner.spec.model_dump_json(indent=2), file=jsf)

        log.info("starting hyperparameter search")
        results = tuner.run()

    best = results.best_result()
    results.save_results(out)
    n_trials = results.num_trials()
    log = log.bind(n_trials=n_trials)

    log.info("finished hyperparameter search", {metric: best[metric]})
    if n_bad := results.num_failed():
        log.warn("%d trials failed", n_bad)
    console.print("[bold yellow]Hyperparameter search completed![/bold yellow]")
    console.print("Best {} is [bold red]{:.3f}[/bold red]".format(metric, best[metric]))
    assert task.duration is not None
    line = "[bold magenta]{}[/bold magenta] trials took [bold cyan]{}[/bold cyan]".format(
        results.num_trials(),
        precisedelta(task.duration),
    )
    if task.system_power:
        line += " and consumed [bold green]{}[/bold green]".format(
            human_metric(task.system_power / 3600, unit="Wh")
        )
    console.print(line)

    log.info("saving final tuned configuration")
    with open(out.with_suffix(".json"), "wt") as jsf:
        print(to_json(best).decode(), file=jsf)
    with open(out.with_name(out.stem + "-pipeline.json"), "wt") as jsf:
        print(results.best_pipeline().model_dump_json(indent=2), file=jsf)

    if use_ray:
        _archive_ray_state(out)


def _archive_ray_state(out: Path):
    _log.info("archiving search state")
    with zipfile.ZipFile(out / "tuning-state.zip", "w") as zipf:
        state_dir = out / "tuning-state"
        for dir, _sds, files in state_dir.walk():
            if dir.name.startswith("checkpoint_"):
                _log.debug("skipping checkpoint directory")
                continue

            _log.debug("adding directory", dir=dir)
            zipf.mkdir(dir.relative_to(out).as_posix())
            for file in files:
                fpath = dir / file
                fpstr = fpath.relative_to(out).as_posix()

                _log.debug("adding file", file=fpstr)
                if fpath.suffix in [".gz", ".zst", ".pkl", ".pt"]:
                    comp = zipfile.ZIP_STORED
                else:
                    comp = zipfile.ZIP_DEFLATED

                zipf.write(fpath, fpstr, compress_type=comp)

    # log.debug("deleting unpacked search state")
    # shutil.rmtree(out / "state")
