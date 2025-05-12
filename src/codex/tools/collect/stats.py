from pathlib import Path

import click
import duckdb

from . import collect


@collect.command("stats")
@click.option("-o", "--output", "db_file", metavar="DB", type=Path, help="output to database DB")
@click.argument("dir", "dirs", nargs=-1, type=Path)
def collect_stats(db_file: Path, dirs: list[Path]):
    "Collect dataset statistics."

    with duckdb.connect(db_file) as db:
        for ds in dirs:
            collect_stats(db, ds)
