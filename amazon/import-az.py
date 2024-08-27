"""
Import Amazon data.

Usage:
    import-az.py --collect-ids (--user | --item) -D DB FILE...
    import-az.py --benchmark --users=DB --items=DB [options] NAME

Options:
    -v, --verbose   include verbose logging output.
    --collect-ids   collect user/item IDs.
    --benchmark     import pre-split benchmark data.
    -D DB, --database=DB
        use database in DB.
    --stat-script=FILE
        run statistics script in FILE.
    FILE            the path to a data file or directory.
    NAME            the name of the data file (without suffix).
"""

import logging
import os.path
from os import fspath
from pathlib import Path
from typing import Iterator

import duckdb
from docopt import ParsedOptions, docopt
from duckdb import DuckDBPyConnection
from sandal.cli import setup_logging

az_root = Path(__file__).parent
_log = logging.getLogger("codex.import-az")


def main(options: ParsedOptions):
    if options["--collect-ids"]:
        collect_ids(options)
    elif options["--benchmark"]:
        import_bench(options)
    else:
        raise RuntimeError("no valid operation mode specified")


def collect_ids(options: ParsedOptions):
    db_fn = options["--database"]
    with duckdb.connect(db_fn) as db:
        if options["--user"]:
            collect_user_ids(db, options["FILE"])
        if options["--item"]:
            collect_item_ids(db, options["FILE"])


def collect_user_ids(db: DuckDBPyConnection, files: list[str]):
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


def collect_item_ids(db: DuckDBPyConnection, files: list[str]):
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
        cat, _tail = src.name.split(".", 2)
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


def scan_files(files: list[str]) -> Iterator[Path]:
    for f in files:
        path = Path(f)
        if path.is_dir():
            for p in path.glob("*.csv.gz"):
                yield p
        else:
            yield path


def import_bench(options: ParsedOptions):
    name = options["NAME"]
    db_fn = name + ".duckdb"
    if os.path.exists(db_fn):
        _log.warning("%s already exists, deleting", db_fn)
        os.unlink(db_fn)

    with duckdb.connect(db_fn) as db:
        _log.info("initializing schema")
        sql = (az_root / "schemas" / "benchmark.sql").read_text()
        db.execute(sql)
        import_part(options, db, name, "train")
        import_part(options, db, name, "valid")
        import_part(options, db, name, "test")

        stat_fn = options["--stat-script"]
        if stat_fn:
            _log.info("loading statistics script from %s", stat_fn)
            stat_sql = Path(stat_fn).read_text()
            db.execute(stat_sql)


def import_part(options: ParsedOptions, db: duckdb.DuckDBPyConnection, name: str, part: str):
    fn = f"{name}.{part}.csv.gz"
    _log.info("reading %s", fn)

    db.execute("CREATE TEMPORARY TABLE raw_ratings AS SELECT * FROM read_csv(?)", [fn])

    _log.debug("inserting user IDs")
    db.execute("""
        INSERT INTO users (user_code)
        SELECT DISTINCT user_id FROM raw_ratings
        WHERE user_id NOT IN (SELECT user_code FROM users)
    """)
    _log.debug("inserting ASINs")
    db.execute("""
        INSERT INTO items (asin)
        SELECT DISTINCT parent_asin FROM raw_ratings
        WHERE parent_asin NOT IN (SELECT asin FROM items)
    """)

    _log.debug("ingesting ratings")
    db.execute(f"""
        INSERT INTO ratings (part, user_id, item_id, rating, timestamp)
        SELECT '{part}', u.user_id, i.item_id, rating, to_timestamp(timestamp)
        FROM raw_ratings r
        JOIN users u ON (r.user_id = u.user_code)
        JOIN items i ON (r.parent_asin = i.asin)
    """)

    db.execute("DROP TABLE raw_ratings")


if __name__ == "__main__":
    assert __doc__ is not None
    args = docopt(__doc__)
    setup_logging(args["--verbose"])
    main(args)
