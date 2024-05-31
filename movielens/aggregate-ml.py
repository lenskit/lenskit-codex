"""
Aggregate MovieLens data statistics for a unified overview.

Usage:
    aggregate-ml.py [options] DS...

Options:
    -v, --verbose   Include verbose logging output.
"""

import logging
import os.path
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import pandas as pd
from docopt import docopt
from sandal import autoroot  # noqa: F401
from sandal.cli import setup_logging

_log = logging.getLogger("codex.aggregate-ml")


def main(options):
    zipf = Path(options["ZIPFILE"])
    _log.info("importing %s", zipf)

    data = open_data(zipf)

    pqf = zipf.with_name("ratings.parquet")

    with data:
        dirname = data.get_dirname()
        with data.archive.open(os.path.join(dirname, data.rating_file)) as rf:
            rate_df = data.read_ratings(rf)
        _log.info("read %d ratings", len(rate_df))

        rate_df["timestamp"] = pd.to_datetime(rate_df["timestamp"], unit="s")

        _log.info("saving %s", pqf)
        rate_df.to_parquet(pqf, index=False, compression="zstd")


def open_data(file: Path) -> MLData:
    name = file.stem
    if name == "ml-100k":
        return ML100K(file)
    elif name == "ml-1m" or name == "ml-10m":
        return MLM(file)
    else:
        return MLCurrent(file)


if __name__ == "__main__":
    args = docopt(__doc__)
    setup_logging(args["--verbose"])
    main(args)
