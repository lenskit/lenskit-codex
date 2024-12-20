"""
Database schemas and support for saving recommendation results.
"""

import logging
from dataclasses import dataclass, field
from typing import NamedTuple, Self
from uuid import UUID

import pandas as pd
from duckdb import ConstantExpression, DuckDBPyConnection
from lenskit.data import ID, ItemList

from codex.dbutil import transaction

_log = logging.getLogger(__name__)
DEFAULT_BATCH_SIZE = 2500

RUN_META_DDL = """
DROP TABLE IF EXISTS run_meta;
CREATE TABLE run_meta (
    run SMALLINT NOT NULL,
    train_run_id UUID NULL,
    eval_run_id UUID NULL,
);
"""
REC_DDL = """
DROP TABLE IF EXISTS recommendations;
CREATE TABLE recommendations (
    run SMALLINT NOT NULL,
    user_id INT NOT NULL,
    item_id INT NOT NULL,
    rank SMALLINT NOT NULL,
    score FLOAT NULL,
);
"""
PRED_DDL = """
DROP TABLE IF EXISTS predictions;
CREATE TABLE predictions (
    run SMALLINT NOT NULL,
    user_id INT NOT NULL,
    item_id INT NOT NULL,
    prediction FLOAT NULL,
    rating FLOAT,
);
"""

USER_METRIC_DDL = """
DROP TABLE IF EXISTS user_metrics;
CREATE TABLE user_metrics (
    run SMALLINT NOT NULL,
    user_id INT NOT NULL,
    time FLOAT NULL,
    nrecs INT,
    ntruth INT,
    ndcg FLOAT NULL,
    recip_rank FLOAT NULL,
    rbp FLOAT NULL,
)
"""


@dataclass
class UserResult:
    user: ID

    test: ItemList
    recommendations: ItemList | None = None
    predictions: ItemList | None = None

    time: float | None = None
    metrics: dict[str, float] = field(default_factory=dict)

    def as_dict(self):
        row: dict[str, float | int | str | bytes | None] = {
            "user_id": self.user,
            "nrecs": len(self.recommendations) if self.recommendations is not None else 0,
            "ntruth": len(self.test),
            "time": self.time,
        }
        row.update(self.metrics)
        return row


class QueuedResult(NamedTuple):
    run: int
    result: UserResult


class ResultDB:
    db: DuckDBPyConnection
    queued: list[QueuedResult]
    store_predictions: bool
    batch_size: int

    def __init__(
        self,
        db: DuckDBPyConnection,
        *,
        store_predictions: bool = False,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.db = db
        self.queued = []
        self.store_predictions = store_predictions
        self.batch_size = batch_size

    def initialize(self):
        self.db.execute(RUN_META_DDL)
        self.db.execute(USER_METRIC_DDL)

        self.db.execute(REC_DDL)
        if self.store_predictions:
            self.db.execute(PRED_DDL)
            self.db.execute("ALTER TABLE user_metrics ADD COLUMN rmse FLOAT")
            self.db.execute("ALTER TABLE user_metrics ADD COLUMN mae FLOAT")

    def add_training(self, run: int, train_id: UUID) -> None:
        # at new training, we write out the current user metrics
        self.flush()

        self.db.execute("INSERT INTO run_meta (run, train_run_id) VALUES (?, ?)", [run, train_id])

    def add_result(self, run: int, result: UserResult) -> None:
        self.queued.append(QueuedResult(run, result))
        if len(self.queued) >= self.batch_size:
            self.flush()

    def log_metrics(self, run: int | None = None, eval_id: UUID | None = None):
        "Log aggregate metrics."
        self.flush()
        if run is not None and eval_id is not None:
            self.db.execute("UPDATE run_meta SET eval_run_id = ? WHERE run = ?", [eval_id, run])

        aggs = "AVG(ndcg), AVG(recip_rank)"
        if self.store_predictions:
            aggs += ", AVG(rmse)"
        if run is not None:
            self.db.execute(f"SELECT {aggs} FROM user_metrics WHERE run = ?", [run])
        else:
            self.db.execute(f"SELECT {aggs} FROM user_metrics")
        row = self.db.fetchone()
        assert row is not None
        if self.store_predictions:
            ndcg, mrr, rmse = row
            _log.info("avg. metrics: NDCG=%.3f, MRR=%.3f, RMSE=%.3f", ndcg, mrr, rmse)
        else:
            ndcg, mrr = row
            _log.info("avg. metrics: NDCG=%.3f, MRR=%.3f", ndcg, mrr)

    def flush(self) -> None:
        if not self.queued:
            return

        to_write = self.queued
        self.queued = []
        _log.debug("writing %d result records", len(to_write))

        with transaction(self.db):
            users = pd.DataFrame.from_records({"run": r.run} | r.result.as_dict() for r in to_write)
            u_cols = [
                "run",
                "user_id",
                _maybe_col("wall_time", users),
                "nrecs",
                "ntruth",
                _maybe_col("ndcg", users),
                _maybe_col("recip_rank", users),
            ]
            if self.store_predictions:
                u_cols += [_maybe_col("rmse", users), _maybe_col("mae", users)]
            self.db.from_df(users).select(*u_cols).insert_into("user_metrics")

            rec_dfs = [
                r.result.recommendations.to_df().assign(run=r.run, user=r.result.user)
                for r in to_write
                if r.result.recommendations is not None
            ]
            if rec_dfs:
                recs = pd.concat(rec_dfs, ignore_index=True)
                self.db.from_df(recs).select(
                    "run",
                    "user",
                    "item",
                    "rank",
                    "score" if "score" in recs.columns else ConstantExpression(None),
                ).insert_into("recommendations")
            pred_dfs = [
                (r.run, r.result.user, r.result.predictions.to_df())
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


def _maybe_col(name, df):
    return name if name in df.columns else ConstantExpression(None)
