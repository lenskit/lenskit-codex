"""
Hyperparameter search space utilities.
"""

from duckdb import DuckDBPyConnection


def save_param_grid(
    db: DuckDBPyConnection, params: dict[str, type | list[int] | list[float] | list[str]]
):
    sql = "CREATE TABLE run_specs (\n"
    sql += "  run_id SERIAL PRIMARY KEY,\n"
    for name, v_or_t in params:
        if isinstance(v_or_t, list):
            pt = type(v_or_t[0])
        else:
            pt = v_or_t

        if pt is int:
            pct = "INTEGER"
        elif pt is float:
            pct = "FLOAT"
        elif pt is str:
            pct = "VARCHAR"

        sql += f"  {name} {pct} NOT NULL,\n"
    sql += ")"

    db.execute(sql)
