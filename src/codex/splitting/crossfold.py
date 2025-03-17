from pathlib import Path
from typing import override

import pandas as pd
from lenskit.data import Dataset, DatasetBuilder, ItemListCollection
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
    dataset: Dataset
    alloc: dict[str, pd.DataFrame]

    def __init__(self, path: Path, src_path: Path):
        _log.info("loading source dataset", file=str(src_path))
        self.dataset = Dataset.load(src_path)
        _log.info("loading split outputs", file=str(path))
        alloc_df = pd.read_parquet(path)
        self.alloc = {str(part): df for (part, df) in alloc_df.groupby("partition")}

    @property
    def parts(self) -> list[str]:
        return list(self.alloc.keys())

    @override
    def get_part(self, part: str) -> TTSplit:
        log = _log.bind(part=part)

        test = self.alloc[part]

        dsb = DatasetBuilder(self.dataset)
        int_name = self.dataset.default_interaction_class()

        log.debug("filtering interactions")
        dsb.filter_interactions(int_name, remove=test)

        ds = dsb.build()

        log.info("loaded %d training interactions", ds.interaction_count)
        return TTSplit(ds, ItemListCollection.from_df(test))
