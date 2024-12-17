from duckdb import DuckDBPyConnection
from lenskit.data import from_interactions_df
from lenskit.splitting import SampleN, crossfold_users

from codex.splitting.spec import CrossfoldSpec, HoldoutSpec


def crossfold_ratings(db: DuckDBPyConnection, cross: CrossfoldSpec, hold: HoldoutSpec):
    if hold.selection == "random":
        hf = SampleN(hold.count)
    else:
        raise ValueError("invalid holdout")

    db.execute("""
        CREATE OR REPLACE TABLE test_alloc (
            partition INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL
        )
    """)

    df = db.sql("SELECT user_id, item_id, rating FROM rf.ratings").to_df()
    ds = from_interactions_df(df)
    if cross.method == "users":
        parts = crossfold_users(ds, cross.partitions, hf, test_only=True)

    for i, split in enumerate(parts):
        test_df = split.test_df  # noqa: F841
        db.execute(
            """
            INSERT INTO test_alloc (partition, user_id, item_id)
            SELECT ?, user_id, item_id FROM test_df
            """,
            [i],
        )
