"""
Aggregate MovieLens data statistics for a unified overview.

Usage:
    aggregate-ml.py [options] DS...

Options:
    -v, --verbose   Include verbose logging output.
    -d DATABASE, --database=DATABASE
                    Connect to specified database [default: ml-stats.duckdb]
"""

import logging
import os.path

from docopt import docopt
from duckdb import DuckDBPyConnection, connect
from sandal import autoroot  # noqa: F401
from sandal.cli import setup_logging

_log = logging.getLogger("codex.aggregate-ml")


def main(options):
    dbfn = options["--database"]
    sets = options["DS"]
    _log.info("summarizing %d data sets", len(sets))
    if os.path.exists(dbfn):
        _log.info("removing %s", dbfn)
        os.unlink(dbfn)

    with connect(dbfn) as db:
        initialize_db(db, sets)
        union_tables(db, "global_stats", sets)
        union_tables(db, "item_stats", sets)
        union_tables(db, "user_stats", sets)


def initialize_db(db: DuckDBPyConnection, sets: list[str]):
    set_names = ", ".join(f"'{n}'" for n in sets)
    db.execute(f"CREATE TYPE ml_set AS ENUM({set_names})")
    for name in sets:
        _log.info("attaching %s", name)
        db.execute(f"ATTACH '{name}/ratings.duckdb' AS {name} (READONLY)")


def union_tables(db: DuckDBPyConnection, table: str, sets: list[str]):
    _log.info("aggregating table %s", table)
    query = f"CREATE TABLE {table} AS "
    selects = [f"SELECT CAST('{n}' AS ml_set) AS dataset, * FROM {n}.{table}" for n in sets]
    query += " UNION ALL ".join(selects)
    _log.debug("query: %s", query)
    db.execute(query)


if __name__ == "__main__":
    args = docopt(__doc__)
    setup_logging(args["--verbose"])
    main(args)
