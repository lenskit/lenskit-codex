"""
Grid-sweep hyperparameter values.

Usage:
    sweep.py [-v] [-p N] MODEL SPLIT RATINGS OUTPUT

Options:
    -v, --verbose           enable verbose logging
    -p N, --partition=N     sweep on test partition N
    MODEL                   name of the model to sweep
    SPLIT                   database file of splits
    OUTPUT                  output database file
"""

import logging
from os import fspath
from pathlib import Path

import duckdb
from docopt import docopt
from sandal import autoroot  # noqa: F401
from sandal.cli import setup_logging
from sandal.project import here
from seedbank import init_file

from codex.models import model_module
from codex.params import param_grid

_log = logging.getLogger("codex.split")


def main():
    opts = docopt(__doc__)
    setup_logging(opts["--verbose"])

    init_file(here("config.toml"))

    mod = model_module(opts["MODEL"])

    split_fn = Path(opts["SPLIT"])
    out_fn = Path(opts["OUTPUT"])

    space = param_grid(mod.sweep_space)
    _log.debug("parameter search space:\n%s", space)

    out_fn.parent.mkdir(exist_ok=True, parents=True)
    with duckdb.connect(fspath(out_fn)) as db:
        db.execute(f"ATTACH '{split_fn}' AS split (READ_ONLY)")
        _log.info("saving run spec table")
        db.execute("DROP TABLE IF EXISTS run_specs")
        db.from_df(space).create("run_specs")


if __name__ == "__main__":
    main()
