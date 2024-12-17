import logging
from dataclasses import dataclass, field
from os import fspath
from pathlib import Path

import duckdb
from lenskit.data import Dataset, ItemListCollection, UserIDKey, from_interactions_df

_log = logging.getLogger(__name__)


@dataclass
class TrainTestData:
    db_path: str
    train_query: str
    test_query: str
    extra_dbs: dict[str, str] = field(default_factory=dict)

    def open_db(self, writable: bool = False) -> duckdb.DuckDBPyConnection:
        _log.debug("opening %s", self.db_path)
        db = duckdb.connect(self.db_path, read_only=self.db_path != ":memory:" and not writable)
        try:
            for name, path in self.extra_dbs.items():
                _log.debug("attaching %s: %s", name, path)
                db.execute(f"ATTACH '{path}' AS {name} (READ_ONLY)")
        except Exception as e:
            db.close()
            raise e

        return db

    def train_ratings(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        return db.query(self.train_query)

    def train_data(self, db: duckdb.DuckDBPyConnection) -> Dataset:
        df = self.train_ratings(db).to_df()
        _log.info("loaded %d train ratings", len(df))
        return from_interactions_df(df)

    def test_ratings(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        return db.query(self.test_query)

    def test_data(self, db: duckdb.DuckDBPyConnection) -> ItemListCollection[UserIDKey]:
        df = self.test_ratings(db).to_df()
        _log.info("loaded %d test ratings", len(df))
        return ItemListCollection.from_df(df, UserIDKey)


def partition_tt_data(
    split: Path, src: Path, partition: int, *, alloc="test_alloc", ratings="src.ratings"
):
    test_q = f"""
SELECT user_id AS user, item_id AS item, rating
FROM {ratings}
JOIN {alloc} USING (user_id, item_id)
WHERE partition = {partition}
ORDER BY user, item
"""
    train_q = f"""
SELECT user_id AS user, item_id AS item, rating
FROM {ratings} LEFT JOIN {alloc} USING (user_id, item_id)
WHERE partition IS NULL OR partition <> {partition}
"""

    return TrainTestData(fspath(split), train_q, test_q, {"src": fspath(src)})


def fixed_tt_data(test: Path, train: list[Path]):
    """
    "Create a train-test data pair from fixed files.
    """

    test_q = f"""
        SELECT user_id AS user, item_id AS item, rating
        FROM read_parquet('{test}')
    """

    train_q = " UNION ALL ".join(
        [
            f"""
            SELECT user_id AS user, item_id AS item, rating
            FROM read_parquet('{pqf}')
        """
            for pqf in train
        ]
    )

    return TrainTestData(":memory:", train_q, test_q)
