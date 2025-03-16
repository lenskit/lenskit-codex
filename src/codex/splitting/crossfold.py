from os import fspath
from pathlib import Path
from typing import override

import duckdb
import pandas as pd
import structlog
from lenskit.data import Dataset, ItemListCollection, UserIDKey, Vocabulary
from lenskit.logging import get_logger
from lenskit.splitting import SampleN, TTSplit, crossfold_users

from ._base import SplitSet
from .spec import CrossfoldSpec, HoldoutSpec

_log = get_logger(__name__)


def crossfold_ratings(data: Dataset, cross: CrossfoldSpec, hold: HoldoutSpec, out: Path):
    if hold.selection == "random":
        hf = SampleN(hold.count)
    else:
        raise ValueError("invalid holdout")

    allocs = {}
    if cross.method == "users":
        parts = crossfold_users(data, cross.partitions, hf, test_only=True)
    else:
        raise ValueError(f"unsupported crossfold method {cross.method}")

    for i, split in enumerate(parts):
        allocs[i] = split.test_df

    allocs = pd.concat(allocs, names=["part"]).reset_index("part")

    _log.info("saving test data", file=out)
    allocs.to_parquet(out, compression="zstd", index=False)


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
            ORDER BY user_id, item_id
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
