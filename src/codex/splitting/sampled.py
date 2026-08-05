from pathlib import Path
from typing import override

import structlog
from lenskit.data import Dataset, ItemListCollection
from lenskit.splitting import SampleN, TTSplit, sample_users

from codex.splitting.spec import HoldoutSpec, SampleSpec

from ._base import SplitSet

_log = structlog.stdlib.get_logger(__name__)


def split_users(data: Dataset, sample: SampleSpec, hold: HoldoutSpec, out: Path):
    if hold.selection == "random":
        hf = SampleN(hold.count)
    else:
        raise ValueError("invalid holdout")

    n_users = data.user_count

    test_users = round(n_users * sample.test_user_fraction)
    test_split = sample_users(data, test_users, hf)

    tune_users = round(n_users * sample.tune_user_fraction)
    tune_split = sample_users(test_split.train, tune_users, hf)

    _log.info("saving training data", dir=out)
    tune_split.train.save(out / "train.dataset")
    _log.info("saving tuning data", dir=out)
    tune_split.test.save_parquet(out / "tune.parquet")
    _log.info("saving testing data", dir=out)
    test_split.test.save_parquet(out / "test.parquet")


class SampledSplitSet(SplitSet):
    """
    A sampled data set.
    """

    base_dir: Path
    log: structlog.stdlib.BoundLogger

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.log = _log.bind(base=str(base_dir))

    @property
    def parts(self):
        return [f.stem for f in self.base_dir.glob("*.parquet")]

    @override
    def get_part(self, part: str) -> TTSplit:
        part_file = self.base_dir / f"{part}.parquet"
        if not part_file.exists():
            raise FileNotFoundError(str(part_file))

        train = Dataset.load(self.base_dir / "train.dataset")
        test = ItemListCollection.load_parquet(part_file)

        return TTSplit(train, test)
