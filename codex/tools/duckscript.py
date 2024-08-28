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

import click
from duckdb import connect
from lenskit.util import Stopwatch

from . import codex

_log = logging.getLogger(__name__)


@codex.command("run-duck-sql")
@click.option("-D", "--database", "db_file", help="database file to open")
@click.argument("SQL", type=Path)
def duckdb_sql(sql: Path, db_file: str | None = None):
    _log.info("reading script from %s", sql)
    script = sql.read_text()

    if db_file:
        _log.info("opening database file %s", db_file)
        db = connect(db_file)
    else:
        _log.info("opening in-memory database")
        db = connect()

    timer = Stopwatch()
    with db:
        db.create_function("log_msg", log_msg)
        db.execute(script)

    _log.info("executed %s in %s", sql, timer)


def log_msg(text: str) -> bool:
    _log.info("%s", text)
    return True
