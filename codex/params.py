"""
Hyperparameter search space utilities.
"""

from itertools import product
from uuid import uuid4

import pandas as pd


def param_grid(params: dict[str, list[int] | list[float] | list[str]]) -> pd.DataFrame:
    records = [[i, uuid4()] + list(vals) for (i, vals) in enumerate(product(*params.values()), 1)]
    return pd.DataFrame.from_records(records, columns=["rec_idx", "rec_id"] + list(params.keys()))
