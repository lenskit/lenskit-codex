import logging
import os.path
from os import fspath
from pathlib import Path

import click
from duckdb import DuckDBPyConnection, connect

from . import movielens

_log = logging.getLogger(__name__)


@movielens.command("aggregate")
@click.option("-d", "--database", type=Path, help="output database file")
@click.argument("NAMES", nargs=-1, required=True)
def aggregate(database: Path, names: list[str]):
    "Aggregate ML data statistics for an integrated view."
    _log.info("summarizing %d data names", len(names))
    if database.exists():
        _log.info("removing %s", database)
        os.unlink(database)

    with connect(fspath(database)) as db:
        initialize_db(db, names)
        union_tables(db, "global_stats", names)
        union_tables(db, "item_stats", names)
        union_tables(db, "user_stats", names)


def initialize_db(db: DuckDBPyConnection, sets: list[str]):
    set_names = ", ".join(f"'{n}'" for n in sets)
    db.execute(f"CREATE TYPE ml_set AS ENUM({set_names})")
    for name in sets:
        _log.info("attaching %s", name)
        db.execute(f"ATTACH '{name}/stats.duckdb' AS {name} (READONLY)")


def union_tables(db: DuckDBPyConnection, table: str, sets: list[str]):
    _log.info("aggregating table %s", table)
    query = f"CREATE TABLE {table} AS "
    selects = [f"SELECT CAST('{n}' AS ml_set) AS dataset, * FROM {n}.{table}" for n in sets]
    query += " UNION ALL ".join(selects)
    _log.debug("query: %s", query)
    db.execute(query)
