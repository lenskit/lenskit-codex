"""
Database schemas and support for saving recommendation results.
"""

import logging
from dataclasses import dataclass
from typing import NamedTuple, Self

import pandas as pd
from duckdb import ConstantExpression, DuckDBPyConnection

from codex.dbutil import transaction
from codex.resources import ResourceMetrics

_log = logging.getLogger(__name__)
DEFAULT_BATCH_SIZE = 2500

TRAIN_METRIC_DDL = """
DROP TABLE IF EXISTS train_stats;
CREATE TABLE train_stats (
    run SMALLINT NOT NULL,
    wall_time FLOAT,
    cpu_time FLOAT,
    cpu_usr FLOAT,
    cpu_sys FLOAT,
    rss_max_kb FLOAT,
);
"""
REC_DDL = """
DROP TABLE IF EXISTS recommendations;
CREATE TABLE recommendations (
    run SMALLINT NOT NULL,
    user INT NOT NULL,
    item INT NOT NULL,
    rank SMALLINT NOT NULL,
    score FLOAT NULL,
);
"""
PRED_DDL = """
DROP TABLE IF EXISTS predictions;
CREATE TABLE predictions (
    run SMALLINT NOT NULL,
    user INT NOT NULL,
    item INT NOT NULL,
    prediction FLOAT NULL,
    rating FLOAT,
);
"""

USER_METRIC_DDL = """
DROP TABLE IF EXISTS user_metrics;
CREATE TABLE user_metrics (
    run SMALLINT NOT NULL,
    user INT NOT NULL,
    wall_time FLOAT NULL,
    nrecs INT,
    ntruth INT,
    recip_rank FLOAT NULL,
    ndcg FLOAT NULL,
)
"""


@dataclass
class UserResult:
    user: int

    test: pd.DataFrame
    recommendations: pd.DataFrame
    predictions: pd.DataFrame | None = None

    resources: ResourceMetrics | None = None

    def as_dict(self):
        row: dict[str, float | int | str | None] = {
            "user": self.user,
            "nrecs": len(self.recommendations),
            "ntruth": len(self.test),
        }
        if self.resources:
            row["wall_time"] = self.resources.wall_time
        return row


class QueuedResult(NamedTuple):
    run: int
    result: UserResult


class ResultDB:
    db: DuckDBPyConnection
    queued: list[QueuedResult]
    batch_size: int

    def __init__(self, db: DuckDBPyConnection, batch_size: int = DEFAULT_BATCH_SIZE):
        self.db = db
        self.queued = []
        self.batch_size = batch_size

    def initialize(self):
        create_result_tables(self.db)

    def add_training(self, run: int, metrics: ResourceMetrics) -> None:
        # at new training, we write out the current user metrics
        self.flush()

        self.db.table("train_stats").insert([run] + list(metrics.dict().values()))

    def add_result(self, run: int, result: UserResult) -> None:
        self.queued.append(QueuedResult(run, result))
        if len(self.queued) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        if not self.queued:
            return

        to_write = self.queued
        self.queued = []
        _log.debug("writing %d result records", len(to_write))

        with transaction(self.db):
            users = pd.DataFrame.from_records({"run": r.run} | r.result.as_dict() for r in to_write)
            self.db.from_df(users).select(
                "run",
                "user",
                "wall_time" if "wall_time" in users.columns else ConstantExpression(None),
                "nrecs",
                "ntruth",
                ConstantExpression(None),
                ConstantExpression(None),
            ).insert_into("user_metrics")

            recs = pd.concat(
                (r.result.recommendations.assign(run=r.run, user=r.result.user) for r in to_write),
                ignore_index=True,
            )
            self.db.from_df(recs).select(
                "run",
                "user",
                "item",
                "rank",
                "score" if "score" in recs.columns else ConstantExpression(None),
            ).insert_into("recommendations")
            pred_dfs = [
                (r.run, r.result.user, r.result.predictions)
                for r in to_write
                if r.result.predictions is not None
            ]
            if pred_dfs:
                preds = pd.concat(
                    (df.assign(run=run, user=user) for (run, user, df) in pred_dfs),
                    ignore_index=True,
                )
                preds = preds[["run", "user", "item", "prediction", "rating"]]
                self.db.from_df(preds).insert_into("predictions")

    def __enter__(self) -> Self:
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.flush()


def create_result_tables(db: DuckDBPyConnection, *, predictions: bool = False):
    db.execute(TRAIN_METRIC_DDL)
    db.execute(USER_METRIC_DDL)

    db.execute(REC_DDL)
    if predictions:
        db.execute(PRED_DDL)
        db.execute("ALTER TABLE user_metrics ADD COLUMN rmse FLOAT")
        db.execute("ALTER TABLE user_metrics ADD COLUMN mae FLOAT")
