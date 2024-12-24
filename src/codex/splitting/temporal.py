from os import fspath
from pathlib import Path
from typing import override

import duckdb
import structlog
from lenskit.data import ItemListCollection, UserIDKey, from_interactions_df
from lenskit.splitting import TTSplit

from ._base import SplitSet
from .spec import TemporalSpec

_log = structlog.stdlib.get_logger(__name__)


class TemporalSplitSet(SplitSet):
    """
    A fixed train/validate/test split.
    """

    source: Path
    db: duckdb.DuckDBPyConnection
    spec: TemporalSpec
    log: structlog.stdlib.BoundLogger

    parts = ["valid", "test"]

    def __init__(self, source: Path, spec: TemporalSpec):
        self.source = source
        self.db = duckdb.connect(fspath(source), read_only=True)
        self.log = _log.bind(file=str(source))

    @override
    def get_part(self, part: str) -> TTSplit:
        lb = ub = None
        match part:
            case "test":
                lb = self.spec.test
            case "valid":
                lb = self.spec.valid
                ub = self.spec.test
            case _:
                raise ValueError(f"invalid part {part}")

        train_query = """
            SELECT user_id, item_id, rating, timestamp
            FROM ratings
            WHERE timestamp < $lb
        """
        test_query = """
            SELECT user_id, item_id, rating, timestamp
            FROM ratings
            WHERE timestamp >= $lb
        """
        if ub is not None:
            test_query += " AND timestamp < $ub"

        self.log.debug("fetching train data")
        self.db.execute(train_query, {"lb": lb, "ub": ub})
        train_df = self.db.fetch_df()
        train = from_interactions_df(train_df)

        self.log.debug("fetching test data")
        self.db.execute(test_query, {"lb": lb, "ub": ub})
        test_df = self.db.fetch_df()
        test = ItemListCollection.from_df(test_df, UserIDKey)

        return TTSplit(train, test)

    def close(self):
        self.db.close()
