from typing import Sequence, override

import pandas as pd
import structlog
from lenskit.data import ItemListCollection, UserIDKey, from_interactions_df
from lenskit.splitting import TTSplit

from ._base import SplitSet

_log = structlog.stdlib.get_logger(__name__)


class FixedSplitSet(SplitSet):
    """
    A fixed train/validate/test split.
    """

    file_base: str
    parts: list[str]
    log: structlog.stdlib.BoundLogger

    def __init__(self, file_base: str, parts: Sequence[str] = ("test", "valid")):
        self.file_base = file_base
        self.parts = list(parts)
        self.log = _log.bind(base=file_base)

    @override
    def get_part(self, part: str) -> TTSplit:
        train = self._read_part("train")
        if part == "test" and "valid" in self.parts:
            valid = self._read_part("valid")
            train = pd.concat([train, valid], ignore_index=True)

        train = from_interactions_df(train)

        test = self._read_part(part)
        test = ItemListCollection.from_df(test, UserIDKey)
        return TTSplit(train, test)

    def _read_part(self, part) -> pd.DataFrame:
        fn = f"{self.file_base}.{part}.parquet"
        self.log.info("reading file", part=part)
        return pd.read_parquet(fn)
