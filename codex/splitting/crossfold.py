import lenskit.crossfold as xf
from duckdb import DuckDBPyConnection

from codex.splitting.spec import CrossfoldSpec, HoldoutSpec


def crossfold_ratings(db: DuckDBPyConnection, cross: CrossfoldSpec, hold: HoldoutSpec):
    if hold.selection == "random":
        hf = xf.SampleN(hold.count)
    else:
        raise ValueError("invalid holdout")

    db.execute("""
        CREATE OR REPLACE TABLE test_alloc (
            partition INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL
        )
    """)

    df = db.sql("SELECT user_id AS user, item_id AS item, rating FROM rf.ratings").to_df()
    if cross.method == "users":
        parts = xf.partition_users(df, cross.partitions, hf)

    for i, (_train_df, test_df) in enumerate(parts):
        db.execute(
            "INSERT INTO test_alloc (part, user_id, item_id) SELECT ?, user, item FROM test_df", [i]
        )
