import logging
from pathlib import Path

from duckdb import DuckDBPyConnection

_log = logging.getLogger(__name__)


def create_ratings_table(db: DuckDBPyConnection, timestamp: bool = True):
    ddl = """
        CREATE TABLE ratings (
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            rating FLOAT NOT NULL,
    """
    if timestamp:
        ddl += "timestamp TIMESTAMP NOT NULL,"
    ddl += ")"
    _log.info("creating ratings table")
    db.execute(ddl)


def create_views(db: DuckDBPyConnection):
    pkg = Path(__file__).parent
    rvf = pkg / "rating_stat_views.sql"
    sql = rvf.read_text()
    db.execute(sql)
