"""
Grid-sweep hyperparameter values.
"""

import json
import logging
import sys
from os import fspath
from pathlib import Path
from typing import cast

import click
import duckdb
import ipyparallel as ipp
import pandas as pd
from humanize import naturalsize
from lenskit.algorithms import Recommender

from codex.data import TrainTestData, fixed_tt_data, partition_tt_data
from codex.inference import connect_cluster, run_recommender
from codex.models import AlgoMod, model_module
from codex.params import param_grid
from codex.results import ResultDB
from codex.training import train_model

from . import codex

_log = logging.getLogger("codex.split")


@codex.group("sweep")
def sweep():
    "Operate on parameter sweeps"
    pass


@sweep.command("run")
@click.option("-n", "--list-length", type=int, metavar="N", help="generate lists of length N")
@click.option("--ratings", "rating_db", type=Path, metavar="FILE", help="load ratings from FILE")
@click.option(
    "--assignments", "assign_db", type=Path, metavar="FILE", help="load test allocations from FILE"
)
@click.option(
    "-p", "--partition", type=int, metavar="N", help="sweep on test partition N", default=0
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
    test_file: Path | None = None,
    rating_db: Path | None = None,
    assign_db: Path | None = None,
    partition: int = 0,
    list_length: int = 100,
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

    predict = "predictions" in mod.outputs
    with (
        duckdb.connect(fspath(out)) as db,
        ResultDB(db, store_predictions=predict) as results,
        connect_cluster() as cluster,
    ):
        db.execute(f"ATTACH '{assign_db}' AS split (READ_ONLY)")
        _log.info("saving run spec table")
        db.from_df(space).create("run_specs")

        sweep_model(results, data, mod, space, list_length, cluster)


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
    mod: AlgoMod,
    space: pd.DataFrame,
    N: int,
    cluster: ipp.Client,
):
    with data.open_db() as test_db:
        test = data.test_ratings(test_db).to_df()

    for point in space.itertuples(index=False):
        _log.info("measuring at point %s", point)
        model = mod.from_config(*point[2:])
        model = Recommender.adapt(model)
        _log.info("training model %s", model)
        model, metrics = train_model(model, data)
        _log.info(
            "finished in %.0fs (%.0fs CPU, %s max RSS)",
            metrics.wall_time,
            metrics.cpu_time,
            naturalsize(metrics.rss_max_kb * 1024),
        )
        run = cast(int, point.run)
        results.add_training(run, metrics)

        _log.info("running recommender")
        for result in run_recommender(
            model, test, N, "predictions" in mod.outputs, cluster=cluster
        ):
            results.add_result(run, result)

        _log.info("run finished")
        results.log_metrics(run)
