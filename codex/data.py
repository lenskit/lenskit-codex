from dataclasses import dataclass
from pathlib import Path

import duckdb


@dataclass
class TrainTestData:
    db_path: Path
    extra_dbs: dict[str, Path]
    train_query: str
    test_query: str

    def open_db(self) -> duckdb.DuckDBPyConnection:
        db = duckdb.connect()
        try:
            for name, path in self.extra_dbs.items():
                db.execute(f"ATTACH '{path}' AS {name} (READ_ONLY)")
        except Exception as e:
            db.close()
            raise e

        return db

    def train_ratings(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        return db.query(self.test_query)

    def test_ratings(self, db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyRelation:
        return db.query(self.test_query)


def partition_tt_data(split: Path, src: Path, partition: int):
    test_q = f"""
SELECT user_id AS user, item_id AS item, rating
FROM test
JOIN src.ratings USING (user_id, item_id)
WHERE partition = {partition}
ORDER BY user, item
"""
    train_q = f"""
SELECT user_id AS user, item_id AS item, rating
FROM test
ANTI JOIN (
    SELECT user_id, item_id FROM src.ratings
    WHERE partition = {partition}
) USING (user_id, item_id)
"""

    return TrainTestData(split, {"src": src}, train_q, test_q)
