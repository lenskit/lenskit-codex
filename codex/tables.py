import logging

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
