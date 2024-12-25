import datetime as dt
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
    spec: TemporalSpec
    db: duckdb.DuckDBPyConnection
    log: structlog.stdlib.BoundLogger

    parts = ["valid", "test"]

    def __init__(self, source: Path, spec: TemporalSpec):
        self.source = source
        self.spec = spec
        self.db = duckdb.connect(fspath(source), read_only=True)
        self.log = _log.bind(file=str(source))

    @override
    def get_part(self, part: str) -> TTSplit:
        log = self.log.bind(part=part)
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
        train_params = {"lb": lb}

        test_query = """
            SELECT user_id, item_id, rating, timestamp
            FROM ratings
            WHERE timestamp >= $lb
        """
        test_params: dict[str, str | int | float | dt.date] = {"lb": lb}
        if ub is not None:
            log.debug("adding upper bound to query")
            test_query += " AND timestamp < $ub"
            test_params["ub"] = ub
        if self.spec.min_train is not None:
            log.debug("adding minimum training ratings to query")
            test_query += """
                AND user_id IN (
                    SELECT user_id FROM ratings WHERE timestamp < $lb
                    GROUP BY user_id HAVING COUNT(*) >= $min
                )
            """
            test_params["min"] = self.spec.min_train

        self.log.debug("fetching train data")
        self.db.execute(train_query, train_params)
        train_df = self.db.fetch_df()
        train = from_interactions_df(train_df)

        self.log.debug("fetching test data")
        self.db.execute(test_query, test_params)
        test_df = self.db.fetch_df()
        test = ItemListCollection.from_df(test_df, UserIDKey)

        return TTSplit(train, test)

    def close(self):
        self.db.close()
