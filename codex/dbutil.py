from contextlib import contextmanager

from duckdb import DuckDBPyConnection, DuckDBPyRelation


def to_dataclass(rel: DuckDBPyRelation, cls, row=None):
    if row is None:
        row = rel.fetchone()
    return cls(**{c[0]: val for (c, val) in zip(rel.description, row)})


@contextmanager
def transaction(db: DuckDBPyConnection):
    db.begin()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
