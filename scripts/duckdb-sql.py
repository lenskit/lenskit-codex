#!/usr/bin/env python3
"""
Run a DuckDB SQL script.

Usage:
    duckdb-sql.py [options] [-d DATABASE] SQL

Options:
    -v, --verbose   enable verbose logging
    -d DATABASE, --database=DATABASE
                    connect to specified database
    SQL             the SQL script file to run
"""

import logging
from pathlib import Path

from docopt import docopt
from duckdb import connect
from sandal.cli import setup_logging

_log = logging.getLogger("codex.duckdb-sql")


def main(options):
    sfile = Path(options["SQL"])
    _log.info("reading script from %s", sfile)
    script = sfile.read_text()

    dbf = options["--database"]
    if dbf:
        _log.info("opening database file %s", dbf)
        db = connect(dbf)
    else:
        _log.info("opening in-memory database")
        db = connect()

    with db:
        db.execute(script)

    _log.info("done!")


if __name__ == "__main__":
    args = docopt(__doc__)
    setup_logging(args["--verbose"])
    main(args)
