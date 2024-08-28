"""
Database schemas and support for saving recommendation results.
"""

from duckdb import DuckDBPyConnection

TRAIN_METRIC_DDL = """
CREATE TABLE train_stats (
    run SMALLINT NOT NULL,
    wall_time FLOAT,
    cpu_time FLOAT,
    cpu_usr FLOAT,
    cpu_sys FLOAT,
    rss_max_kb FLOAT,
)
"""
REC_DDL = """
CREATE TABLE recommendations (
    run SMALLINT NOT NULL,
    user INT NOT NULL,
    item INT NOT NULL,
    rank SMALLINT NOT NULL,
    score FLOAT NULL,
)
"""
PRED_DDL = """
CREATE TABLE predictions (
    run SMALLINT NOT NULL,
    user INT NOT NULL,
    item INT NOT NULL,
    prediction FLOAT NULL,
    rating FLOAT,
)
"""

USER_METRIC_DDL = """
CREATE TABLE user_metrics (
    run SMALLINT NOT NULL,
    user INT NOT NULL,
    nrecs INT,
    ntruth INT,
    recip_rank FLOAT NULL,
    ndcg FLOAT NULL,
)
"""


def create_result_tables(db: DuckDBPyConnection, *, predictions: bool = False):
    db.execute(TRAIN_METRIC_DDL)
    db.execute(USER_METRIC_DDL)

    db.execute(REC_DDL)
    if predictions:
        db.execute(PRED_DDL)
        db.execute("ALTER TABLE user_metrics ADD COLUMN rmse FLOAT")
        db.execute("ALTER TABLE user_metrics ADD COLUMN mae FLOAT")
