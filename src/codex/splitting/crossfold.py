from os import fspath
from pathlib import Path
from typing import override

import duckdb
import structlog
from lenskit.data import ItemListCollection, UserIDKey, Vocabulary, from_interactions_df
from lenskit.data.matrix import MatrixDataset
from lenskit.splitting import SampleN, TTSplit, crossfold_users

from ._base import SplitSet
from .spec import CrossfoldSpec, HoldoutSpec

_log = structlog.stdlib.get_logger(__name__)


def crossfold_ratings(db: duckdb.DuckDBPyConnection, cross: CrossfoldSpec, hold: HoldoutSpec):
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


class CrossfoldSplitSet(SplitSet):
    db: duckdb.DuckDBPyConnection
    log: structlog.stdlib.BoundLogger

    def __init__(self, path: Path, src_path: Path):
        self.log = _log.bind(db=str(path))
        self.log.debug("connecting")
        self.db = duckdb.connect(fspath(path), read_only=True)
        self.db.execute(f"ATTACH '{src_path}' AS src")

    @property
    def parts(self) -> list[str]:
        self.db.execute("SELECT DISTINCT partition FROM test_alloc ORDER BY partition")
        return [str(part) for (part,) in self.db.fetchall()]

    @override
    def get_part(self, part: str) -> TTSplit:
        log = self.log.bind(part=part)
        test_query = """
            SELECT user_id, item_id, rating
            FROM src.ratings
            JOIN test_alloc USING (user_id, item_id)
            WHERE partition = ?
        """
        train_query = """
            WITH test_pairs AS (SELECT user_id, item_id FROM test_alloc WHERE partition = ?)
            SELECT user_id, item_id, rating, timestamp
            FROM src.ratings ANTI JOIN test_pairs USING (user_id, item_id)
        """
        log.debug("querying for test ratings")
        self.db.execute(test_query, [part])
        test_df = self.db.fetch_df()
        test = ItemListCollection.from_df(test_df, UserIDKey)
        log.info("loaded %d test users", len(test))
        log.debug("querying for train ratings")
        self.db.execute(train_query, [part])
        train_df = self.db.fetch_df()

        log.debug("fetching entity IDs")
        self.db.execute("SELECT DISTINCT user_id FROM src.ratings")
        users = self.db.fetchnumpy()["user_id"]
        users = Vocabulary(users)
        self.db.execute("SELECT DISTINCT item_id FROM src.ratings")
        items = self.db.fetchnumpy()["item_id"]
        items = Vocabulary(items)

        ds = MatrixDataset(users, items, train_df)

        log.info("loaded %d training interactions", ds.interaction_count)
        return TTSplit(ds, test)

    def close(self):
        self.db.close()
