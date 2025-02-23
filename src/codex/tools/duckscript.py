#!/usr/bin/env python3
"""
Run a DuckDB SQL script.
"""

import re
from pathlib import Path
from string import Template

import click
from duckdb import DuckDBPyConnection, StatementType
from lenskit.logging import get_logger
from lenskit.util import Stopwatch

from codex.dbutil import db_connect

from . import codex

_log = get_logger(__name__)
SEGMENT_RE = re.compile(r"^--#segment\s+(.*?)\s*$", re.MULTILINE)


@codex.command("sql")
@click.option("--read-only", help="open database read-only", is_flag=True)
@click.option("--keep-going", help="keep running even if the script fails", is_flag=True)
@click.option(
    "-D",
    "--define",
    "defines",
    metavar="name=val",
    multiple=True,
    help="define variables for queries",
)
@click.option("-f", "--file", "sql", type=Path, help="script file to run")
@click.argument("DBFILES", nargs=-1)
def duckdb_sql(
    sql: Path,
    dbfiles: list[str],
    read_only: bool = False,
    keep_going: bool = False,
    defines: list[str] = [],
):
    global _log
    log = _log.bind(script=str(sql))
    log.info("reading script source")
    var_defs = {}
    for d in defines:
        name, _, var = d.partition("=")
        var_defs[name] = var

    script = sql.read_text()

    for dbf in dbfiles:
        timer = Stopwatch()
        _log = log.bind(db=str(dbf))
        with db_connect(dbf, read_only=read_only) as db:
            try:
                run_script(db, script, var_defs)
            except Exception as e:
                _log.error("script failed: %s", e)
                if not keep_going:
                    raise e

        log.info("finished executing in %s", timer)


def run_script(db: DuckDBPyConnection, script: str, defines: dict[str, str]):
    pos = 0
    options = {}
    while (m := SEGMENT_RE.search(script, pos)) is not None:
        sp = m.start()
        _log.debug("found segment", position=sp)
        if script[pos:sp].strip():
            run_segment(db, script[pos:sp], options, defines)
        options = parse_options(m.group(1))
        _log.debug("segment options: %s", options, position=sp)
        pos = m.end() + 1

    if script[pos:].strip():
        run_segment(db, script[pos:], options, defines)


def run_segment(
    db: DuckDBPyConnection, segment: str, options: dict[str, bool | str], defines: dict[str, str]
):
    parts = db.extract_statements(segment)
    try:
        db.begin()
        for part in parts:
            query = part.query
            if defines:
                _log.debug("interpolating templates")
                qt = Template(query)
                query = qt.substitute(defines)

            _log.debug("executing query", type=part.type, result=part.expected_result_type)
            db.execute(query)
            if part.type == StatementType.SELECT:
                print(db.fetch_df())
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
