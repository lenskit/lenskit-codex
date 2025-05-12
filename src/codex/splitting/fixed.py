from pathlib import Path
from typing import override

import structlog
from lenskit.data import Dataset, ItemListCollection
from lenskit.splitting import TTSplit

from ._base import SplitSet

_log = structlog.stdlib.get_logger(__name__)


class FixedSplitSet(SplitSet):
    """
    A fixed train/validate/test split.
    """

    base_dir: Path
    log: structlog.stdlib.BoundLogger

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.log = _log.bind(base=str(base_dir))

    @property
    def parts(self):
        return [f.parent.name for f in self.base_dir.glob("*/train.dataset")]

    @override
    def get_part(self, part: str) -> TTSplit:
        part_dir = self.base_dir / part
        if not part_dir.exists():
            raise FileNotFoundError(str(part_dir))

        train = Dataset.load(part_dir / "train.dataset")
        test = ItemListCollection.load_parquet(part_dir / "test.parquet")

        return TTSplit(train, test)
