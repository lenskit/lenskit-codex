"""
Split ratings / interaction data for evaluation.

Usage:
    split.py [-v] SPEC

Options:
    -v, --verbose       enable verbose logging
    SPEC                path to split specification TOML file
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

from codex.splitting.crossfold import crossfold_ratings
from codex.splitting.spec import load_split_spec

_log = logging.getLogger("codex.split")


def main():
    opts = docopt(__doc__)
    setup_logging(opts["--verbose"])

    init_file(here("config.toml"))

    path = Path(opts["SPEC"])
    _log.info("loading spec from %s", path)
    split = load_split_spec(Path(opts["SPEC"]))
    _log.debug("loaded split config: %s", split)

    db_file = path.with_suffix(".duckdb")
    src_file = db_file.parent / split.source
    with duckdb.connect(fspath(db_file)) as db:
        _log.info("attaching %s", src_file)
        db.execute(f"ATTACH '{src_file}' AS rf")

        if split.method == "crossfold":
            assert split.crossfold
            assert split.holdout
            crossfold_ratings(db, split.crossfold, split.holdout)


if __name__ == "__main__":
    main()
