from os import fspath
from pathlib import Path

import structlog

from ._base import SplitSet
from .crossfold import CrossfoldSplitSet
from .fixed import FixedSplitSet
from .spec import SplitSpec, load_split_spec
from .temporal import TemporalSplitSet

_log = structlog.stdlib.get_logger(__name__)

__all__ = [
    "SplitSet",
    "SplitSpec",
    "load_split_set",
    "load_split_spec",
]


def load_split_set(path: Path) -> SplitSet:
    log = _log.bind(path=str(path))
    if path.exists():
        log.debug("loading split spec")
        spec = load_split_spec(path)
        src = path.parent / spec.source
        log.debug("source file: %s", src)

        match spec.method:
            case "temporal":
                assert spec.temporal is not None
                return TemporalSplitSet(src, spec.temporal)
            case "crossfold":
                assert spec.crossfold is not None
                assert spec.holdout is not None
                return CrossfoldSplitSet(path.with_suffix(".parquet"), src)

    elif path.with_name(path.name + ".train.parquet").exists():
        log.debug("found parquet file, using fixed set")
        return FixedSplitSet(fspath(path))

    else:
        log.error("neither file nor train.parquet exists")
        raise RuntimeError("cannot detect type of split set")
