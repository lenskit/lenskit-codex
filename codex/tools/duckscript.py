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
import re
from pathlib import Path

import click
from duckdb import DuckDBPyConnection, connect
from lenskit.util import Stopwatch

from . import codex

_log = logging.getLogger(__name__)
SEGMENT_RE = re.compile(r"^--#segment\s+(.*?)\s*$", re.MULTILINE)


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
                run_script(db, script)
            except Exception as e:
                _log.error("script failed: %s", e)
                if not keep_going:
                    raise e

        _log.info("executed %s in %s", sql, timer)


def log_msg(text: str) -> bool:
    _log.info("%s", text)
    return True


def run_script(db: DuckDBPyConnection, script: str):
    pos = 0
    options = {}
    while (m := SEGMENT_RE.search(script, pos)) is not None:
        sp = m.start()
        _log.debug("found segment at position %d", sp)
        if script[pos:sp].strip():
            run_segment(db, script[pos:sp], options)
        options = parse_options(m.group(1))
        _log.debug("segment options: %s", options)
        pos = m.end() + 1

    if script[pos:].strip():
        run_segment(db, script[pos:], options)


def run_segment(db: DuckDBPyConnection, segment: str, options: dict[str, bool | str]):
    try:
        db.begin()
        db.execute(segment)
        db.commit()
    except Exception as e:
        db.rollback()
        if options.get("err", "fail") == "continue":
            _log.info("segment failed, continuing: %s", e)
        else:
            _log.error("segment failed: %s", e)
            raise e


def parse_options(options: str) -> dict[str, bool | str]:
    parts = re.split(r"\s+", options)
    opts = {}
    for p in parts:
        m = re.match(r"(\w+)=(.*)", p)
        if m:
            opts[m.group(1)] = m.group(2)
        else:
            opts[p] = True

    return opts
