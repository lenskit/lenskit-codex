"""
Grid-sweep hyperparameter values.
"""

import json
import shutil
import sys
from itertools import product
from os import fspath
from pathlib import Path

import click
import duckdb
import structlog
from lenskit.logging import item_progress

from codex.cfgid import config_id
from codex.cluster import ensure_cluster_init
from codex.collect import NDJSONCollector
from codex.inference import recommend_and_save
from codex.modelcfg import load_config
from codex.params import param_grid
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.splitting import load_split_set
from codex.training import train_task

from . import codex

_log = structlog.stdlib.get_logger(__name__)


@codex.group("sweep")
def sweep():
    "Operate on parameter sweeps"
    pass


@sweep.command("run")
@click.option(
    "-n", "--list-length", type=int, metavar="N", default=500, help="generate lists of length N"
)
@click.option("--split", "split", type=Path, help="path to the split spec (or base file)")
@click.option("-N", "--ds-name", help="name of the dataset to split")
@click.option(
    "-p",
    "--test-part",
    metavar="PART",
    help="validate on PART",
)
@click.argument("MODEL")
@click.argument("OUT", type=Path)
def run_sweep(
    model: str,
    out: Path,
    list_length: int,
    split: Path,
    ds_name: str | None = None,
    test_part: str = "valid",
):
    log = _log.bind(model=model)
    mod_cfg = load_config(model)
    if not mod_cfg.sweep:
        log.error("model is not sweepable")
        sys.exit(5)

    space = param_grid(mod_cfg.sweep)
    _log.debug("parameter search space:\n%s", space)

    if out.exists():
        log.warning("output already exists, removing", out=str(out))
        shutil.rmtree(out)
    out.mkdir(exist_ok=True, parents=True)

    ensure_cluster_init()

    names = list(mod_cfg.sweep.keys())
    points = list(product(*mod_cfg.sweep.values()))
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
        NDJSONCollector(out / "run-user-metrics.ndjson.zst") as metric_out,
    ):
        data = split_set.get_part(test_part)
        for i, point in enumerate(points, 1):
            point = dict(zip(names, point))
            plog = log.bind(**point)
            run_id = config_id(
                {
                    "model": mod_cfg.name,
                    "dataset": ds_name,
                    "params": "point",
                }
            )
            plog.info("training and evaluating")
            mod_inst = mod_cfg.instantiate(point)
            pipe, tr_task = train_task(mod_inst, data.train, data_info)
            with open(out / "training.json", "a") as jsf:
                print(tr_task.model_dump_json(), file=jsf)

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
                    out / "recommendations" / shard,
                    out / "predictions" / shard if mod_cfg.predictor else None,
                    metric_out,
                    meta={"run": i},
                )

            with open(out / "inference.json", "a") as jsf:
                print(test_task.model_dump_json(), file=jsf)

            with open(out / "runs.json", "a") as jsf:
                run = {
                    "run": i,
                    "run_id": str(run_id),
                    "train_task": tr_task.model_dump(mode="json"),
                    "test_task": test_task.model_dump(mode="json"),
                    "metrics": result.list_summary()["mean"].to_dict(),
                }
                print(json.dumps(run), file=jsf)

            plog.info("run finished, RBP=%.4f", result.list_summary().loc["RBP", "mean"])
            pb.update()


@sweep.command("export")
@click.argument("DATABASE", type=Path)
@click.argument("METRIC")
def export_best_results(database: Path, metric: str):
    order = "ASC" if metric == "rmse" else "DESC"

    with duckdb.connect(fspath(database), read_only=True) as db:
        um_cols = db.table("user_metrics").columns
        um_aggs = ", ".join(
            f"AVG({col}) AS {col}" for col in um_cols if col not in {"run", "user_id", "wall_time"}
        )
        _log.info("fetching output results")
        query = f"""
            SELECT COLUMNS(rs.* EXCLUDE rec_id),
                tm.wall_time AS TrainTime,
                tm.cpu_time AS TrainCPU,
                rss_max_kb / 1024 AS TrainMemMB,
                {um_aggs}
            FROM run_specs rs
            JOIN train_stats tm USING (run)
            JOIN user_metrics um USING (run)
            GROUP BY rs.*
            ORDER BY {metric} {order}
        """
        top = db.sql(query)
        print(top.limit(5).to_df())

        csv_fn = database.with_suffix(".csv")
        _log.info("writing results to %s", csv_fn)
        top.write_csv(fspath(csv_fn))

        json_fn = database.with_suffix(".json")
        _log.info("writing best configuration to %s", json_fn)
        best_row = top.fetchone()
        assert best_row is not None
        best = dict(zip(top.columns, best_row))
        json_fn.write_text(json.dumps(best, indent=2) + "\n")
