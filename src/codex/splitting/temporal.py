import datetime as dt
from pathlib import Path
from typing import override

import structlog
from lenskit.data import Dataset, ListILC
from lenskit.splitting import TTSplit, split_global_time

from ._base import SplitSet
from .spec import TemporalSpec

_log = structlog.stdlib.get_logger(__name__)


class TemporalSplitSet(SplitSet):
    """
    A temporal train/validate/test split.
    """

    source: Path
    spec: TemporalSpec
    data: Dataset
    log: structlog.stdlib.BoundLogger

    parts = ["valid", "test"]

    def __init__(self, source: Path, spec: TemporalSpec):
        self.source = source
        self.spec = spec
        self.data = Dataset.load(source)
        self.log = _log.bind(file=str(source), name=self.data.name)

    @override
    def get_part(self, part: str) -> TTSplit:
        log = self.log.bind(part=part)
        lb = ub = None
        midnight = dt.datetime.min.time()
        match part:
            case "test":
                lb = dt.datetime.combine(self.spec.test, midnight)
            case "valid":
                lb = dt.datetime.combine(self.spec.tune, midnight)
                ub = dt.datetime.combine(self.spec.test, midnight)
            case _:
                raise ValueError(f"invalid part {part}")

        log.info("splitting data", test_lb=str(lb), test_ub=str(ub))
        split = split_global_time(self.data, lb, ub)
        test = ListILC(["user_id"])
        users = split.train.user_stats()
        users = users.index[users["count"] > 0]
        for key, value in split.test:
            if key.user_id in users:
                test.add(value, *key)

        log.info("kept %d of %d test users", len(test), len(split.test))
        split.test = test
        return split
