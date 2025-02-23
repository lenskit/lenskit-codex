from contextlib import contextmanager
from os import PathLike, fspath
from typing import Any

import duckdb
import structlog
from duckdb import DuckDBPyConnection, DuckDBPyRelation
from lenskit.logging import get_logger

from .layout import codex_relpath, codex_root

_log = get_logger(__name__)


def db_connect(path: str | PathLike[str], read_only: bool = True) -> DuckDBPyConnection:
    """
    Convenience function to connect to a database and set up our user-defined
    functions and default options.  Connections default to read-only.
    """
    path = fspath(path)
    log = _log.bind(db=str(codex_relpath(path)))
    log.info("opening database", writable=not read_only)
    cxn = duckdb.connect(path, read_only=read_only)
    log.debug("creating functions")
    cxn.create_function("log_msg", _duck_logger(log))
    cxn.create_function(
        "project_path",
        _duck_project_path,
        side_effects=False,
    )
    return cxn


def to_dataclass(rel: DuckDBPyRelation, cls, row: tuple[Any, ...] | None = None):
    if row is None:
        row = rel.fetchone()
    return cls(**{c[0]: val for (c, val) in zip(rel.description, row)})  # type: ignore


@contextmanager
def transaction(db: DuckDBPyConnection):
    db.begin()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e


def _duck_logger(log: structlog.stdlib.BoundLogger):
    def log_msg(text: str) -> bool:
        log.info("%s", text)
        return True

    return log_msg


def _duck_project_path(parts: str | list[str]) -> str:
    path = codex_root()
    if isinstance(parts, str):
        path = path / parts
    else:
        for p in parts:
            path = path / p
    return fspath(path)
