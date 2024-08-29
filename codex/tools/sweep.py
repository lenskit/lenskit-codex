"""
Grid-sweep hyperparameter values.
"""

import json
import logging
from os import fspath
from pathlib import Path

import click
import duckdb
import ipyparallel as ipp
import pandas as pd
from humanize import naturalsize
from lenskit.algorithms import Recommender

from codex.data import TrainTestData, partition_tt_data
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
@click.option("-p", "--partition", type=int, metavar="N", help="sweep on test partition N")
@click.option("-n", "--list-length", type=int, metavar="N", help="generate lists of length N")
@click.option("--ratings", "rating_db", type=Path, metavar="FILE", help="load ratings from FILE")
@click.option(
    "--assignments", "assign_db", type=Path, metavar="FILE", help="load test allocations from FILE"
)
@click.argument("MODEL")
@click.argument("OUT", type=Path)
def run_sweep(
    rating_db: Path,
    assign_db: Path,
    model: str,
    out: Path,
    partition: int = 0,
    list_length: int = 100,
):
    mod = model_module(model)

    space = param_grid(mod.sweep_space)
    _log.debug("parameter search space:\n%s", space)

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

        tt = partition_tt_data(assign_db, rating_db, partition)

        sweep_model(results, tt, mod, space, list_length, cluster)


@sweep.command("export")
@click.argument("DATABASE", type=Path)
@click.argument("METRIC")
def export_best_results(database: Path, metric: str):
    order = "ASC" if metric == "rmse" else "DESC"

    with duckdb.connect(fspath(database), read_only=True) as db:
        um_cols = db.table("user_metrics").columns
        um_aggs = ", ".join(
            f"AVG({col}) AS {col}" for col in um_cols if col not in {"run", "user", "wall_time"}
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
        results.add_training(point.run, metrics)

        _log.info("running recommender")
        for result in run_recommender(
            model, test, N, "predictions" in mod.outputs, cluster=cluster
        ):
            results.add_result(point.run, result)

        _log.info("run finished")
        aggs = "AVG(ndcg), AVG(recip_rank)"
        if "predictions" in mod.outputs:
            aggs += " AVG(rmse)"
        results.db.execute(f"SELECT {aggs} FROM user_metrics WHERE run = ?", [point.run])
        row = results.db.fetchone()
        assert row is not None
        if "predictions" in mod.outputs:
            ndcg, mrr, rmse = row
            _log.info("avg. metrics: NDCG=%.3f, MRR=%.3f, RMSE=%.3f", ndcg, mrr, rmse)
        else:
            ndcg, mrr = row
            _log.info("avg. metrics: NDCG=%.3f, MRR=%.3f", ndcg, mrr)
