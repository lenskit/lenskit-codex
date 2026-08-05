from pathlib import Path

import click
from lenskit.data import Dataset
from lenskit.logging import get_logger

from codex.splitting.crossfold import crossfold_ratings
from codex.splitting.sampled import split_users
from codex.splitting.spec import load_split_spec

from . import codex

_log = get_logger(__name__)


@codex.command("split")
@click.argument("FILE", type=Path)
def split_data(file: Path):
    """
    Split data for cross-validation and other randomized splitting designs.
    """

    log = _log.bind(file=file)
    log.info("loading split specification")
    split = load_split_spec(file)
    log = log.bind(method=split.method)

    src_path = file.parent / split.source
    log.info("loading source data", src=src_path)
    data = Dataset.load(src_path)

    match split.method:
        case "crossfold":
            out_file = file.with_suffix(".parquet")
            assert split.crossfold
            assert split.holdout
            crossfold_ratings(data, split.crossfold, split.holdout, out_file)

        case "sample-users":
            out_dir = file.with_suffix("")
            assert split.sample
            assert split.holdout
            split_users(data, split.sample, split.holdout, out_dir)

        case _:
            log.error("unsupported split method")
            raise ValueError(f"cannot split {split.method}")
