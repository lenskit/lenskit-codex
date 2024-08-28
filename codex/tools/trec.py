import logging
from os import fspath
from pathlib import Path

import click
import duckdb

from . import codex

_log = logging.getLogger("codex.split")


@codex.group("trec")
def trec():
    "Work with TREC-format data."
    pass


@trec.group("export")
def export():
    "Export data into TREC formats."
    pass


@export.command("qrels")
@click.argument("FILE", type=Path)
def export_qrels(file: Path):
    if file.suffix != ".parquet":
        _log.info("only parquet files can be exported at present")

    outf = file.with_suffix(".qrels.gz")
    with duckdb.connect() as db:
        _log.info("reading test data from %s", file)
        tbl = db.read_parquet(fspath(file))
        qrels = tbl.query(
            "ratings",
            """
            SELECT user_id, 0, item_id, CAST(rating AS int)
            FROM ratings
            ORDER BY user_id, item_id
            """,
        )
        _log.info("saving qrels to %s", outf)
        qrels.write_csv(fspath(outf), sep="\t", header=False, compression="gzip")
