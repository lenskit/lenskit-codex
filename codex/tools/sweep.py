"""
Grid-sweep hyperparameter values.
"""

import json
import sys
from os import fspath
from pathlib import Path
from typing import cast

import click
import duckdb
import pandas as pd
import ray
import structlog
from lenskit.pipeline import Trainable

from codex.data import TrainTestData, fixed_tt_data, partition_tt_data
from codex.inference import run_recommender
from codex.models import ModelMod, model_module
from codex.params import param_grid
from codex.pipeline import base_pipeline
from codex.results import ResultDB

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
@click.option("--ratings", "rating_db", type=Path, metavar="FILE", help="load ratings from FILE")
@click.option(
    "--assignments", "assign_db", type=Path, metavar="FILE", help="load test allocations from FILE"
)
@click.option(
    "-p", "--partition", type=int, metavar="N", default=0, help="sweep on test partition N"
)
@click.option("--test", "test_file", type=Path, metavar="FILE", help="Parquet file of test data")
@click.option(
    "--train",
    "train_files",
    type=Path,
    metavar="FILE",
    help="Parquet file of training data",
    multiple=True,
)
@click.argument("MODEL")
@click.argument("OUT", type=Path)
def run_sweep(
    model: str,
    out: Path,
    train_files: list[Path],
    partition: int,
    list_length: int,
    test_file: Path | None = None,
    rating_db: Path | None = None,
    assign_db: Path | None = None,
):
    mod = model_module(model)

    space = param_grid(mod.sweep_space)
    _log.debug("parameter search space:\n%s", space)

    if test_file:
        if assign_db or rating_db:
            _log.error("--train/--test not compatible with alloc options")
            sys.exit(2)
        if not train_files:
            _log.error("--test specified without training data")
            sys.exit(2)

        data = fixed_tt_data(test_file, train_files)

    elif assign_db:
        if rating_db is None:
            _log.error("must specify --ratings with --assignments")
            sys.exit(2)

        if test_file or train_files:
            _log.error("--train and --test incompatible with --assignments")
            sys.exit(2)

        data = partition_tt_data(assign_db, rating_db, partition)

    out.parent.mkdir(exist_ok=True, parents=True)
    if out.exists():
        _log.warning("%s already exists, removing", out)
        out.unlink()

    ray.init()
    predict = "predictions" in mod.outputs
    with (
        duckdb.connect(fspath(out)) as db,
        ResultDB(db, store_predictions=predict) as results,
    ):
        _log.info("saving run spec table")
        db.from_df(space).create("run_specs")

        sweep_model(results, data, model, mod, space, list_length)


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


def sweep_model(
    results: ResultDB,
    data: TrainTestData,
    name: str,
    mod: ModelMod,
    space: pd.DataFrame,
    N: int,
):
    log = _log.bind(model=name)

    with data.open_db() as test_db:
        test = data.test_data(test_db)
        train = data.train_data(test_db)

    pipe = base_pipeline(name)
    log.info("training base pipeline")
    pipe.train(train)

    for point in space.itertuples(index=False):
        plog = log.bind(**point._asdict())
        plog.info("preparing for measurement", point)
        model = mod.from_config(*point[2:])
        if isinstance(model, Trainable):
            plog.info("training model", point)
            model.train(train)
        pipe.replace_component("scorer", model)

        run = cast(int, point.run)
        results.add_training(run)

        _log.info("running recommender")
        for result in run_recommender(pipe, test, N, "predictions" in mod.outputs):
            results.add_result(run, result)

        _log.info("run finished")
        results.log_metrics(run)
