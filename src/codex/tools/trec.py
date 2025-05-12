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
@click.option("-o", "--output", type=Path, metavar="FILE", help="Write output to FILE.")
@click.argument("FILE", type=Path)
def export_qrels(output: Path, file: Path):
    "Export QREL files from truth data."
    if file.suffix != ".parquet":
        _log.info("only parquet files can be exported at present")

    with connect() as db:
        _log.info("reading test data from %s", file)
        tbl = db.read_parquet(fspath(file))
        qrels = tbl.query(
            "ratings",
            """
            WITH unpacked AS (SELECT user_id, UNNEST(items) AS item FROM ratings)
            SELECT user_id, 0, item.item_id, CAST(item.rating AS int)
            FROM unpacked
            ORDER BY user_id, item.item_id
            """,
        )
        _log.info("saving qrels to %s", output)
        qrels.write_csv(fspath(output), sep="\t", header=False, compression="gzip")


@export.command("runs")
@click.option("-o", "--output", type=Path)
@click.argument("RECS", nargs=-1, type=Path)
def export_runs(output: Path, recs: list[Path]):
    "Export runs in TREC-compatible format."
    # <query id><iteration><document id><rank><score>[<run id>]

    with connect() as db:
        db.execute("""
            CREATE TABLE recs (
                user_id VARCHAR, iter VARCHAR, item_id VARCHAR, rank INT, score FLOAT, run VARCHAR
            )
        """)
        for rd in recs:
            rf = rd / "recommendations.parquet"
            _log.info("loading recommendations from %s", rf)
            query = f"""
                WITH unpacked AS (SELECT part, user_id, UNNEST(items) AS item FROM '{fspath(rf)}')
                INSERT INTO recs
                SELECT user_id, part, item.item_id, item.rank, ROUND(COALESCE(item.score, 0), 4), ?
                FROM unpacked
            """
            db.execute(query, [rd.name])

        _log.info("saving runs to %s", output)
        db.execute(
            f"COPY (SELECT * FROM recs ORDER BY run, user_id, iter, rank) TO '{fspath(output)}'"
            " (FORMAT CSV, SEP '\\t', HEADER FALSE)"
        )
