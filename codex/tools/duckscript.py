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
@click.option("--read-only", help="open database read-only", is_flag=True)
@click.option("--keep-going", help="keep running even if the script fails", is_flag=True)
@click.option("-f", "--file", "sql", type=Path, help="script file to run")
@click.argument("DBFILES", nargs=-1)
def duckdb_sql(sql: Path, dbfiles: list[str], read_only: bool = False, keep_going: bool = False):
    _log.info("reading script from %s", sql)
    script = sql.read_text()

    for dbf in dbfiles:
        _log.info("opening database file %s", dbf)
        timer = Stopwatch()
        with connect(dbf, read_only=read_only) as db:
            db.create_function("log_msg", log_msg)
            try:
                db.begin()
                db.execute(script)
                db.commit()
            except Exception as e:
                db.rollback()
                _log.error("script failed: %s", e)
                if not keep_going:
                    raise e

        _log.info("executed %s in %s", sql, timer)


def log_msg(text: str) -> bool:
    _log.info("%s", text)
    return True
