import logging
import re
from dataclasses import dataclass
from os import fspath
from pathlib import Path

import duckdb

_log = logging.getLogger(__name__)


@dataclass
class TrainTestData:
    db_path: Path
    extra_dbs: dict[str, Path]
    train_query: str
    test_query: str

    def open_db(self, writable: bool = False) -> duckdb.DuckDBPyConnection:
        _log.debug("opening %s", self.db_path)
        db = duckdb.connect(fspath(self.db_path), read_only=not writable)
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

    def test_ratings(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        return db.query(self.test_query)


def partition_tt_data(
    split: Path, src: Path, partition: int, *, alloc="test", ratings="src.ratings"
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

    return TrainTestData(split, {"src": src}, train_q, test_q)


def fixed_tt_data(db: Path, test: str, *, train: list[str] | None = None):
    test_q = f"""
SELECT user_id AS user, item_id AS item, rating
FROM ratings
WHERE partition = '{test}'
ORDER BY user, item
"""
    if train:
        parts = ", ".join([f"'{s}'" for s in train])
        train_q = f"""
SELECT user_id AS user, item_id AS item, rating
FROM ratings
WHERE partition in ({parts})
"""
    else:
        train_q = f"""
SELECT user_id AS user, item_id AS item, rating
FROM ratings
WHERE partition IS NULL OR partition <> '{test}'
"""

    return TrainTestData(db, {}, train_q, test_q)


def parse_parts(spec: str) -> list[str]:
    m = re.match(r"^(\d+)-(\d+)$", spec)
    if m:
        return [str(i) for i in range(int(m[1]), int(m[2]) + 1)]
    else:
        return spec.split(",")
