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


def load_sweep_iters(model, split=None, method="random") -> pd.DataFrame:
    base = Path()
    if split is None:
        split = DATA_INFO.default_split

    with open(base / "sweeps" / split / f"{model}-{method}" / "iterations.ndjson", "rt") as jsf:
        run_data = [json.loads(line) for line in jsf]
    return pd.json_normalize(run_data)


def load_sweep_result(model, split=None, method="random") -> dict:
    base = Path()
    if split is None:
        split = DATA_INFO.default_split

    with open(base / "sweeps" / split / f"{model}-{method}.json", "rt") as jsf:
        return json.load(jsf)


def show_param_space(space):
    import ray.tune.search.sample

    flat = _flatten_param_space(space, "", {})
    tbl = PrettyTable()
    tbl.set_style(TableStyle.MARKDOWN)
    tbl.field_names = ["Parameter", "Type", "Distribution", "Values"]
    tbl.align = "c"
    tbl.align["Parameter"] = "l"

    for k, v in flat.items():
        dist = str(v.sampler)
        if isinstance(v, ray.tune.search.sample.Categorical):
            values = ", ".join(v.categories)
        elif dist == "Normal":
            values = "μ={}, σ={}".format(v.sampler.mean, v.sampler.md)
        else:
            values = "{} ≤ $x$ ≤ {}".format(v.lower, v.upper)
        tbl.add_row([k, v.__class__.__name__, dist, values])

    return Markdown(str(tbl))


def _flatten_param_space(space, prefix, out):
    for k, v in space.items():
        if isinstance(v, dict):
            _flatten_param_space(v, prefix + k + ".", out)
        else:
            out[prefix + k] = v

    return out
