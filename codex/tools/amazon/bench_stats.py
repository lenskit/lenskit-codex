"""
Collect stats on benchmark data.
"""

import logging
from os import fspath
from pathlib import Path

import click
import duckdb

from . import amazon

_log = logging.getLogger(__name__)


@amazon.command("bench-stats")
@click.argument("DIR", type=Path)
@click.argument("DBFILE", type=Path)
def bench_stats(dir: Path, dbfile: Path):
    "Collect statistics from pre-computed benchmark splits."

    _log.info("opening database %s", dbfile)
    with duckdb.connect(fspath(dbfile)) as db:
        db.execute("""

        """)
