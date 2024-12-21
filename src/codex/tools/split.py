import logging
from os import fspath
from pathlib import Path

import click
import duckdb

from codex.splitting.crossfold import crossfold_ratings
from codex.splitting.spec import load_split_spec

from . import codex

_log = logging.getLogger("codex.split")


@codex.command("split")
@click.argument("FILE", type=Path)
def split_data(file: Path):
    _log.info("loading spec from %s", file)
    split = load_split_spec(file)
    _log.debug("loaded split config: %s", split)

    db_file = file.with_suffix(".duckdb")
    src_file = db_file.parent / split.source
    with duckdb.connect(fspath(db_file)) as db:
        _log.info("attaching %s", src_file)
        db.execute(f"ATTACH '{src_file}' AS rf (READ_ONLY)")

        if split.method == "crossfold":
            assert split.crossfold
            assert split.holdout
            crossfold_ratings(db, split.crossfold, split.holdout)
