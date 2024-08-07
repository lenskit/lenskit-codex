"""
Grid-sweep hyperparameter values.

Usage:
    sweep.py [-v] [-p N] MODEL SPLIT RATINGS OUTPUT

Options:
    -v, --verbose           enable verbose logging
    -p N, --partition=N     sweep on test partition N
    MODEL                   name of the model to sweep
    SPLIT                   database file of splits
    RATINGS                 database file of original rating data
    OUTPUT                  output database file
"""

import logging
import sys
from multiprocessing.managers import SharedMemoryManager
from os import fspath
from pathlib import Path
from typing import Any, cast

import duckdb
import pandas as pd
from docopt import docopt
from sandal import autoroot  # noqa: F401
from sandal.cli import setup_logging
from sandal.project import here
from seedbank import init_file

from codex.data import TrainTestData, partition_tt_data
from codex.models import AlgoMod, model_module
from codex.params import param_grid
from codex.training import train_model

_log = logging.getLogger("codex.split")


def main():
    opts = docopt(__doc__)
    setup_logging(opts["--verbose"])

    init_file(here("config.toml"))

    mod = model_module(opts["MODEL"])

    split_fn = Path(opts["SPLIT"])
    src_fn = Path(opts["RATINGS"])
    out_fn = Path(opts["OUTPUT"])

    space = param_grid(mod.sweep_space)
    _log.debug("parameter search space:\n%s", space)

    out_fn.parent.mkdir(exist_ok=True, parents=True)
    with duckdb.connect(fspath(out_fn)) as db:
        db.execute(f"ATTACH '{split_fn}' AS split (READ_ONLY)")
        _log.info("saving run spec table")
        db.execute("DROP TABLE IF EXISTS run_specs")
        db.from_df(space).create("run_specs")

        part = opts.get("--partition")
        if part is not None:
            tt = partition_tt_data(split_fn, src_fn, int(part))
        else:
            _log.error("no train-test selection")
            sys.exit(10)

        sweep_model(db, tt, cast(AlgoMod, mod), space)


def sweep_model(
    db: duckdb.DuckDBPyConnection, data: TrainTestData, mod: AlgoMod, space: pd.DataFrame
):
    for point in space.itertuples():
        model = mod.from_config(*point[2:])
        with SharedMemoryManager() as mgr:
            _log.info("training model")
            model, metrics = train_model(model, data, mgr)


if __name__ == "__main__":
    main()
