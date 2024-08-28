"""
Grid-sweep hyperparameter values.

Usage:
    sweep.py [-v] [-p N] [-n N] MODEL SPLIT RATINGS DATABASE
    sweep.py [-v] --export DATABASE METRIC

Options:
    -v, --verbose
        enable verbose logging
    -p N, --partition=N
        sweep on test partition N
    -n N, --list-length=N
        generate recommendation lists of length N [default: 100]
    --export
        export the final sweep results
    MODEL
        name of the model to sweep
    SPLIT
        database file of splits
    RATINGS
        database file of original rating data
    DATABASE
        sweep result database file
    METRIC
        the metric to use for selecting best results
"""

import json
import logging
from os import fspath
from pathlib import Path

import click
import duckdb
import pandas as pd
from humanize import naturalsize
from lenskit import batch, topn
from lenskit.algorithms import Recommender
from lenskit.metrics.predict import mae, rmse

from codex.data import TrainTestData, partition_tt_data
from codex.models import AlgoMod, model_module
from codex.params import param_grid
from codex.resources import METRIC_COLUMN_DDL
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
    with duckdb.connect(fspath(out)) as db:
        db.execute(f"ATTACH '{assign_db}' AS split (READ_ONLY)")
        _log.info("saving run spec table")
        db.from_df(space).create("run_specs")
        db.execute(f"CREATE TABLE train_metrics (rec_idx INT NOT NULL, {METRIC_COLUMN_DDL})")
        db.execute("""
            CREATE TABLE recommendations (
                rec_idx INT NOT NULL,
                user INT NOT NULL,
                item INT NOT NULL,
                rank INT NOT NULL,
                score FLOAT NULL,
            )
        """)
        db.execute("""
            CREATE TABLE user_metrics (
                rec_idx INT NOT NULL,
                user INT NOT NULL,
                nrecs INT,
                ntruth INT,
                recip_rank FLOAT,
                ndcg FLOAT,
            )
        """)
        if "predictions" in mod.outputs:
            db.execute("""
                CREATE TABLE predictions (
                    rec_idx INT NOT NULL,
                    user INT NOT NULL,
                    item INT NOT NULL,
                    prediction FLOAT NULL,
                    rating FLOAT,
                )
            """)
            db.execute("ALTER TABLE user_metrics ADD COLUMN rmse FLOAT")
            db.execute("ALTER TABLE user_metrics ADD COLUMN mae FLOAT")

        tt = partition_tt_data(assign_db, rating_db, partition)

        sweep_model(db, tt, mod, space, list_length)


@sweep.command("export")
@click.argument("DATABASE", type=Path)
@click.argument("METRIC")
def export_best_results(database: Path, metric: str):
    order = "ASC" if metric == "rmse" else "DESC"

    with duckdb.connect(fspath(database), read_only=True) as db:
        um_cols = db.table("user_metrics").columns
        um_aggs = ", ".join(
            f"AVG({col}) AS {col}" for col in um_cols if col not in {"rec_idx", "user"}
        )
        _log.info("fetching output results")
        query = f"""
            SELECT COLUMNS(rs.* EXCLUDE rec_id),
                wall_time AS TrainTime,
                cpu_time AS TrainCPU,
                rss_max_kb / 1024 AS TrainMemMB,
                {um_aggs}
            FROM run_specs rs
            JOIN train_metrics tm USING (rec_idx)
            JOIN user_metrics um USING (rec_idx)
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
    db: duckdb.DuckDBPyConnection, data: TrainTestData, mod: AlgoMod, space: pd.DataFrame, N: int
):
    with data.open_db() as test_db:
        test = data.test_ratings(test_db).to_df()
    test_users = test["user"].unique()

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
        db.table("train_metrics").insert([point.rec_idx] + list(metrics.dict().values()))

        _log.info("generating recommendations")
        n_jobs = 1 if len(test_users) < 1000 else None
        recs = batch.recommend(model, test_users, N, n_jobs=n_jobs)
        db.from_df(
            recs.assign(rec_idx=point.rec_idx)[db.table("recommendations").columns]
        ).insert_into("recommendations")

        _log.info("measuring recommendations")
        rla = topn.RecListAnalysis()
        rla.add_metric(topn.recip_rank)
        rla.add_metric(topn.ndcg)
        umetrics = rla.compute(recs, test, include_missing=True)
        assert umetrics.index.name == "user"
        _log.info("avg. NDCG: %.3f", umetrics["ndcg"].mean())

        if "predictions" in mod.outputs:
            _log.info("predicting test ratings")
            preds = batch.predict(model, test, n_jobs=n_jobs)
            db.from_df(
                preds.assign(rec_idx=point.rec_idx)[
                    ["rec_idx", "user", "item", "prediction", "rating"]
                ]
            ).insert_into("predictions")
            u_pm = preds.groupby("user").apply(
                lambda df: pd.Series(
                    {
                        "rmse": rmse(df["prediction"], df["rating"]),
                        "mae": mae(df["prediction"], df["rating"]),
                    }
                ),
                include_groups=False,
            )
            umetrics = umetrics.join(u_pm, how="outer")
            _log.info("avg. RMSE: %.3f", umetrics["rmse"].mean())

        umetrics = umetrics.reset_index().assign(rec_idx=point.rec_idx)

        db.from_df(umetrics[db.table("user_metrics").columns]).insert_into("user_metrics")
