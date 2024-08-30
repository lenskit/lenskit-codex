import logging
from collections.abc import Generator
from os import fspath
from pathlib import Path

import click
from duckdb import connect

from . import collect

_log = logging.getLogger(__name__)

METRIC_AGG_DDL = """
DROP TABLE IF EXISTS run_files;
DROP SEQUENCE IF EXISTS run_fileno;
CREATE SEQUENCE run_fileno START 1;
CREATE TABLE run_files (
    fileno INT PRIMARY KEY DEFAULT nextval('run_fileno'),
    filename VARCHAR NOT NULL UNIQUE,
);
DROP TABLE IF EXISTS run_metrics;
CREATE TABLE run_metrics (
    fileno INT NOT NULL,
    run TINYINT NOT NULL,
    ndcg FLOAT,
    mrr FLOAT,
    user_rmse FLOAT
);
DROP TABLE IF EXISTS user_metrics;
CREATE TABLE user_metrics (
    fileno INT NOT NULL,
    run TINYINT NOT NULL,
    wall_time FLOAT,
    nrecs INT,
    ntruth INT,
    ndcg FLOAT,
    recip_rank FLOAT,
    rmse FLOAT,
    mae FLOAT,
);
"""


@collect.command("metrics")
@click.option("--view-script", type=Path, help="SQL script to create derived views")
@click.option("-g", "--glob", help="Glob to select files from directories.")
@click.argument("DBFILE", type=Path)
@click.argument("INPUTS", type=Path, nargs=-1, required=True)
def collect_metrics(
    dbfile: Path, inputs: list[Path], view_script: Path | None = None, glob: str | None = None
):
    "Collect metrics from runs across DB files."
    _log.info("opening output database %s", dbfile)
    with connect(fspath(dbfile)) as db:
        db.execute(METRIC_AGG_DDL)
        for src_db in find_inputs(inputs, glob):
            _log.info("reading %s", src_db)
            db.execute(f"ATTACH '{src_db}' AS src (READ_ONLY)")

            db.execute(
                "INSERT INTO run_files (filename) VALUES (?) RETURNING fileno", [src_db.as_posix()]
            )
            fnrow = db.fetchone()
            assert fnrow is not None
            (fileno,) = fnrow

            db.execute("""
                SELECT column_name FROM duckdb_columns()
                WHERE database_name = 'src'
                AND table_name = 'user_metrics'
            """)
            src_cols = [r[0] for r in db.fetchall()]

            ucols = "ndcg, recip_rank"
            cols = "ndcg, mrr"
            agg = "AVG(ndcg) AS ndcg, AVG(recip_rank) AS mrr"
            if "rmse" in src_cols:
                ucols += ", rmse, mae"
                cols += ", user_rmse"
                agg += ", AVG(rmse) AS user_rmse"

            db.execute(
                f"""
                    INSERT INTO run_metrics (fileno, run, {cols})
                    SELECT ?, run, {agg}
                    FROM src.user_metrics
                    GROUP BY run
                """,
                [fileno],
            )

            db.execute(
                f"""
                    INSERT INTO user_metrics (fileno, run, {ucols})
                    SELECT ?, run, {ucols}
                    FROM src.user_metrics
                """,
                [fileno],
            )

            _log.debug("detaching source database")
            db.execute("DETACH src")

        if view_script is not None:
            _log.info("running %s", view_script)
            sql = view_script.read_text()
            db.execute(sql)


def find_inputs(inputs: list[Path], glob: str | None) -> Generator[Path]:
    for src in inputs:
        if src.is_dir():
            if glob is None:
                _log.warn("no glob specified, defaulting to **/*.duckdb")
                glob = "**/*.duckdb"
            yield from src.glob(glob)
        else:
            yield src
