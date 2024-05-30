from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
from duckdb import DuckDBPyConnection


@dataclass
class GlobalRatingStats:
    n_ratings: int
    n_users: int
    n_items: int
    first_rating: datetime
    last_rating: datetime


def global_rating_stats(db: DuckDBPyConnection) -> GlobalRatingStats:
    db.execute("""
        SELECT COUNT(*) AS n_ratings,
            COUNT(DISTINCT user_id) AS n_users,
            COUNT(DISTINCT item_id) AS n_items,
            MIN(timestamp) AS first_rating,
            MAX(timestamp) AS last_rating
        FROM ratings
    """)
    res = db.fetchone()
    return GlobalRatingStats(**{c[0]: val for (c, val) in zip(db.description, res)})


def pop_gini(df: pd.DataFrame, val_col="n_ratings"):
    col = df[val_col].sort_values()
    n = len(col)
    ranks = np.arange(n) + 1
    num = 2 * np.sum(ranks * col)
    denom = n * np.sum(col)
    mod = (n + 1) / n
    return num / denom - mod
