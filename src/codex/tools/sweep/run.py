"""
Grid-sweep hyperparameter values.
"""

import sys
from itertools import product
from pathlib import Path
from typing import Generator, Literal

import click
import numpy as np
from lenskit.logging import get_logger, item_progress
from pydantic import JsonValue
from scipy import stats

from codex.cfgid import config_id
from codex.config import rng_seed
from codex.inference import recommend_and_save
from codex.modelcfg import ModelConfig, load_config
from codex.outputs import RunOutput
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.splitting import load_split_set
from codex.training import train_task

from . import sweep

_log = get_logger(__name__)


@sweep.command("run")
@click.option(
    "-n", "--list-length", type=int, metavar="N", default=100, help="generate lists of length N"
)
@click.option("--split", "split", type=Path, help="path to the split spec (or base file)")
@click.option("-N", "--ds-name", help="name of the dataset to split")
@click.option(
    "-p",
    "--test-part",
    metavar="PART",
    help="validate on PART",
)
@click.option("--grid", "method", flag_value="grid", help="use grid search")
@click.option("--random", "method", flag_value="random", help="use random search")
@click.argument("MODEL")
@click.argument("OUT", type=Path)
def run_sweep(
    model: str,
    out: Path,
    list_length: int,
    split: Path,
    method: Literal["grid", "random"],
    ds_name: str | None = None,
    test_part: str = "valid",
):
    log = _log.bind(model=model)
    mod_cfg = load_config(model)
    if not mod_cfg.search.grid:
        log.error("model is not sweepable")
        sys.exit(5)

    output = RunOutput(out)
    output.initialize()

    match method:
        case "grid":
            points = list(search_grid(mod_cfg))
        case "random":
            points = list(search_random(mod_cfg))
        case _:
            assert False, f"invalid method {method}"

    log.info("sweeping %d points", len(points))
    data_info = DataModel(dataset=ds_name, split=split.stem, part=test_part)

    with (
        item_progress("points", len(points)) as pb,
        CodexTask(
            label=f"sweep {model}",
            tags=["sweep"],
            scorer=ScorerModel(name=model),
            data=data_info,
        ),
        load_split_set(split) as split_set,
        output.user_metric_collector() as metric_out,
    ):
        data = split_set.get_part(test_part)
        for i, point in enumerate(points, 1):
            run_id = config_id(
                {
                    "model": mod_cfg.name,
                    "dataset": ds_name,
                    "params": point,
                }
            )
            plog = log.bind(run_id=run_id, **point)
            plog.info("training and evaluating")
            mod_inst = mod_cfg.instantiate(point)
            pipe, tr_task = train_task(mod_inst, data.train, data_info)
            output.record_log("training", tr_task)

            shard = f"run={i}"
            with CodexTask(
                label=f"recommend {model}",
                tags=["recommend"],
                reset_hwm=True,
                scorer=ScorerModel(name=model, config=mod_inst.params),
                data=data_info,
            ) as test_task:
                result = recommend_and_save(
                    pipe,
                    data.test,
                    list_length,
                    output.recommendations_hive_path / shard,
                    output.predictions_hive_path / shard if mod_cfg.predictor else None,
                    metric_out,
                    meta={"run": i},
                )

            output.record_log("inference", test_task)

            output.record_log(
                "run",
                {
                    "run": i,
                    "run_id": str(run_id),
                    "train_task": tr_task.model_dump(mode="json"),
                    "test_task": test_task.model_dump(mode="json"),
                    "params": mod_inst.params,
                    "metrics": result.list_summary()["mean"].to_dict(),
                },
            )

            plog.info("run finished, RBP=%.4f", result.list_summary().loc["RBP", "mean"])
            pb.update()

        output.repack_output_lists()


def search_grid(mod_cfg: ModelConfig) -> Generator[dict[str, JsonValue], None, None]:
    if not mod_cfg.search.grid:
        _log.error("no search grid specified", name=mod_cfg.name)
        raise RuntimeError("no search grid")

    names = list(mod_cfg.search.grid.keys())
    for point in product(*mod_cfg.search.grid.values()):
        yield dict(zip(names, point))


def search_random(mod_cfg: ModelConfig):
    if not mod_cfg.search.params:
        _log.error("no search parameters specified", name=mod_cfg.name)
        raise RuntimeError("no search parameters")

    seed = rng_seed("sweep", mod_cfg.name)
    rng = np.random.default_rng(seed)

    for i in range(mod_cfg.search.random_points):
        point = {}
        for name, cfg in mod_cfg.search.params.items():
            if cfg.type == "categorical":
                point[name] = rng.choice(cfg.values)
            elif cfg.space == "linear":
                if cfg.type == "integer":
                    dist = stats.randint(cfg.min, cfg.max)
                    point[name] = dist.rvs(random_state=rng)
                else:
                    dist = stats.uniform(cfg.min, cfg.max)
                    point[name] = dist.rvs(random_state=rng)
            else:
                shift = 0
                if cfg.min == 0:
                    dist = stats.loguniform(cfg.min + 1e-6, cfg.max + 1e-6)
                    shift = 1e-6
                else:
                    dist = stats.loguniform(cfg.min, cfg.max)
                val = dist.rvs(random_state=rng) - shift
                if cfg.type == "integer":
                    val = round(val)
                point[name] = val

        yield point
