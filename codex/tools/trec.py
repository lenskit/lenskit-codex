import logging
from os import fspath
from pathlib import Path

import click
from duckdb import connect

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
    "Export QREL files from truth data."
    if file.suffix != ".parquet":
        _log.info("only parquet files can be exported at present")

    outf = file.with_suffix(".qrels.gz")
    with connect() as db:
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


@export.command("runs")
@click.option("-r", "--run", type=int, help="select a single run to output")
@click.argument("DB", type=Path)
@click.argument("OUT", type=Path)
def export_runs(db: Path, out: Path, run: int | None = None):
    "Export runs in TREC-compatible format."
    # <query id><iteration><document id><rank><score>[<run id>]

    with connect(fspath(db), read_only=True) as cxn:
        if run is not None:
            params = [run]
            filter = "WHERE run == ?"
        else:
            params = []
            filter = ""

        query = f"""
            SELECT user, 0, item, rank, ROUND(COALESCE(score, 0), 4), run
            FROM recommendations
            {filter}
            ORDER BY run, user, rank
        """
        _log.info("saving run to %s", out)
        cxn.execute(
            f"COPY ({query}) TO '{fspath(out)}' (FORMAT CSV, SEP '\\t', HEADER FALSE)", params
        )
