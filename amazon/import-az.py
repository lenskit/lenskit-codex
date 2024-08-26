"""
Import Amazon data.

Usage:
    import-az.py [-v] --benchmark NAME

Options:
    -v, --verbose   include verbose logging output.
    --benchmark     import pre-split benchmark data.
    NAME            the name of the data file (without suffix)
"""

import logging
import os.path
from pathlib import Path

import duckdb
from docopt import ParsedOptions, docopt
from sandal.cli import setup_logging

az_root = Path(__file__).parent
_log = logging.getLogger("codex.import-az")


def main(options: ParsedOptions):
    if options["--benchmark"]:
        import_bench(options)
    else:
        raise RuntimeError("no valid operation mode specified")


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
