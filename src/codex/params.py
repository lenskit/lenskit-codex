"""
Hyperparameter search space utilities.
"""

import json
from itertools import product
from uuid import NAMESPACE_URL, UUID, uuid5

import pandas as pd
from pydantic import JsonValue

NS_CONFIG = uuid5(NAMESPACE_URL, "https://ns.lenskit.org/param-space")


def param_grid(params: dict[str, list[JsonValue]]) -> pd.DataFrame:
    records = [
        [i, param_id(dict(zip(params.keys(), vals)))] + list(vals)
        for (i, vals) in enumerate(product(*params.values()), 1)
    ]
    return pd.DataFrame.from_records(records, columns=["run", "rec_id"] + list(params.keys()))


def param_id(params: dict[str, JsonValue]) -> UUID:
    return uuid5(NS_CONFIG, json.dumps(params))
