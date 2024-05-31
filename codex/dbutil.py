from duckdb import DuckDBPyRelation


def to_dataclass(rel: DuckDBPyRelation, cls, row=None):
    if row is None:
        row = rel.fetchone()
    return cls(**{c[0]: val for (c, val) in zip(rel.description, row)})
