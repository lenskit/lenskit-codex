import logging
from os import fspath
from pathlib import Path

import click
from duckdb import connect

from . import collect

_log = logging.getLogger(__name__)

METRIC_AGG_DDL = """
DROP TABLE IF EXISTS run_metrics;
CREATE TABLE run_metrics (
    file VARCHAR NOT NULL,
    run TINYINT NOT NULL,
    ndcg FLOAT,
    mrr FLOAT,
    user_rmse FLOAT
)
"""


@collect.command("metrics")
@click.option("--view-script", type=Path, help="SQL script to create derived views")
@click.argument("DBFILE", type=Path)
@click.argument("INPUTS", type=Path, nargs=-1, required=True)
def collect_metrics(dbfile: Path, inputs: list[Path], view_script: Path | None = None):
    "Collect metrics from runs across DB files."

    _log.info("opening output database %s", dbfile)
    with connect(fspath(dbfile)) as db:
        db.execute(METRIC_AGG_DDL)
        for src_db in inputs:
            _log.info("reading %s", src_db)
            db.execute(f"ATTACH '{src_db}' AS src (READ_ONLY)")

            db.execute("""
                SELECT column_name FROM duckdb_columns()
                WHERE database_name = 'src'
                AND table_name = 'user_metrics'
            """)
            src_cols = [r[0] for r in db.fetchall()]

            cols = "ndcg, mrr"
            agg = "AVG(ndcg) AS ndcg, AVG(recip_rank) AS mrr"
            if "rmse" in src_cols:
                cols += ", user_rmse"
                agg += ", AVG(rmse) AS user_rmse"

            db.execute(
                f"""
                    INSERT INTO run_metrics (file, run, {cols})
                    SELECT ?, run, {agg}
                    FROM src.user_metrics
                    GROUP BY run
                """,
                [str(src_db)],
            )

            _log.debug("detaching source database")
            db.execute("DETACH src")

        if view_script is not None:
            _log.info("running %s", view_script)
            sql = view_script.read_text()
            db.execute(sql)
