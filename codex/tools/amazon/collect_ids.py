import logging
import sys
from os import fspath
from pathlib import Path
from typing import Iterator, Literal

import click
import duckdb

from . import amazon

_log = logging.getLogger(__name__)


@amazon.command("collect-ids")
@click.option("--user", "mode", help="collect user IDs", flag_value="user")
@click.option("--item", "mode", help="collect item IDs", flag_value="item")
@click.option("-D", "--database", help="save IDs in DATABASE", required=True)
@click.argument("FILE", nargs=-1, type=Path)
def collect_ids(mode: Literal["user", "item"] | None, database: str, file: list[Path]):
    "Collect user and item identifiers for Amazon"
    if mode is None:
        _log.fatal("must specify one of --user or --item")
        sys.exit(2)

    _log.info("opening database %s", database)
    with duckdb.connect(database) as db:
        match mode:
            case "user":
                collect_user_ids(db, file)
            case "item":
                collect_item_ids(db, file)
            case _:
                assert False, "reached without valid mode"


def scan_files(files: list[Path]) -> Iterator[Path]:
    for path in files:
        if path.is_dir():
            for p in path.glob("*.csv.gz"):
                yield p
        else:
            yield path


def collect_user_ids(db: duckdb.DuckDBPyConnection, files: list[Path]):
    _log.info("initializing user ID DB")
    db.execute("CREATE SEQUENCE uid_sequence START 1;")
    db.execute("""
        CREATE TABLE users (
            user_id INT PRIMARY KEY DEFAULT nextval('uid_sequence'),
            user_code VARCHAR NOT NULL UNIQUE,
        );
    """)

    for src in scan_files(files):
        _log.info("scanning %s", src)
        rel = db.read_csv(fspath(src))
        rel.query(
            "ratings",
            """
                INSERT INTO users (user_code)
                SELECT DISTINCT user_id
                FROM ratings
                WHERE user_id NOT IN (SELECT user_code FROM users)
            """,
        )


def collect_item_ids(db: duckdb.DuckDBPyConnection, files: list[Path]):
    _log.info("initializing item ID DB")
    db.execute("CREATE SEQUENCE iid_sequence START 1;")
    db.execute("""
        CREATE TABLE items (
            item_id INT PRIMARY KEY DEFAULT nextval('uid_sequence'),
            asin VARCHAR NOT NULL UNIQUE,
            item_cat VARCHAR NOT NULL,
        );
    """)

    for src in scan_files(files):
        _log.info("scanning %s", src)
        cat, _tail = src.name.split(".", 1)
        rel = db.read_csv(fspath(src))
        rel.query(
            "ratings",
            f"""
                INSERT INTO items (item_code, item_at)
                SELECT DISTINCT parent_asin, '{cat}'
                FROM ratings
                WHERE parent_asin NOT IN (SELECT asin FROM items)
            """,
        )
