import logging
from os import fspath
from pathlib import Path

import click
import duckdb

from . import amazon

_log = logging.getLogger(__name__)


@amazon.command("import-bench")
@click.option("--users", help="User ID database", required=True)
@click.option("--items", help="Item ID database", required=True)
@click.argument("FILE", nargs=-1, type=Path)
def import_bench(user_db, item_db, files: list[Path]):
    "Convert a pre-split benchmark data file."

    with duckdb.connect() as db:
        db.execute("ATTACH ? AS udb", [user_db])
        db.execute("ATTACH ? AS idb", [item_db])

        for src in files:
            dst = src.with_name(src.name.replace(".csv.gz", ".parquet"))
            _log.info("scanning %s", src)
            rel = db.read_csv(fspath(src))
            mapped = rel.query(
                "raw_ratings",
                """
                SELECT u.user_id, i.item_id, rating, timestamp
                FROM raw_ratings r
                JOIN udb.users u ON (u.user_code = r.user_id)
                JOIN idb.items i ON (i.asin = r.parent_asin)
            """,
            )
            _log.info("writing to %s", dst)
            mapped.write_parquet(fspath(dst), compression="zstd")
