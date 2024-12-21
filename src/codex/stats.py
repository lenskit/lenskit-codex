from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass
class GlobalRatingStats:
    n_ratings: int
    n_users: int
    n_items: int
    first_rating: datetime
    last_rating: datetime


def pop_gini(df: pd.DataFrame, val_col="n_ratings"):
    col = df[val_col].sort_values()
    n = len(col)
    ranks = np.arange(n) + 1
    num = 2 * np.sum(ranks * col)
    denom = n * np.sum(col)
    mod = (n + 1) / n
    return num / denom - mod
