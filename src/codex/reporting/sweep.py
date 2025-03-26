"""
Utilities for reporting sweeps.
"""

import json
from pathlib import Path

import pandas as pd
from IPython.display import Markdown
from prettytable import PrettyTable, TableStyle

from .data import DATA_INFO


def load_sweep_runs(model, split=None, method="random") -> pd.DataFrame:
    base = Path()
    if split is None:
        split = DATA_INFO.default_split

    with open(base / "sweeps" / split / f"{model}-{method}" / "trials.ndjson", "rt") as jsf:
        run_data = [json.loads(line) for line in jsf]
    return pd.json_normalize(run_data)


def show_param_space(space):
    flat = _flatten_param_space(space, "", {})
    tbl = PrettyTable()
    tbl.set_style(TableStyle.MARKDOWN)
    tbl.field_names = ["Parameter", "Distribution", "Min", "Max"]
    tbl.align = "c"
    tbl.align["Parameter"] = "l"

    for k, v in flat.items():
        dist = str(v.sampler)
        if dist == "Normal":
            dist = "Normal(μ={}, σ={})".format(v.sampler.mean, v.sampler.md)
        tbl.add_row([k, dist, v.lower, v.upper])

    return Markdown(str(tbl))


def _flatten_param_space(space, prefix, out):
    for k, v in space.items():
        if isinstance(v, dict):
            _flatten_param_space(v, prefix + k + ".", out)
        else:
            out[prefix + k] = v

    return out
