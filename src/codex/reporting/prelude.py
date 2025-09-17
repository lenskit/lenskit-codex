import json
import logging
import re
import warnings
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotnine as pn
import pyarrow as pa
import pyarrow.compute as pc
import statsmodels.api as sm
import statsmodels.formula.api as smf
import tqdm
from humanize import metric, naturalsize
from IPython.display import Markdown
from itables import show as show_df
from lenskit.logging import get_logger
from rich.console import Console
from tabulate import tabulate

from ..config import get_config
from .data import DATA_INFO, filter_part
from .plots import (
    DEFAULTS,
    label_memory,
    scale_x_memory,
    scale_x_metric,
    scale_y_memory,
    scale_y_metric,
)
from .sweep import load_sweep_iters, load_sweep_result, load_sweep_runs, show_param_space

warnings.filterwarnings("ignore", "IProgress not found", tqdm.TqdmWarning)
logging.getLogger("ray.widgets").setLevel(logging.ERROR)

log = get_logger("notebook")
rich = Console()
CONFIG = get_config()

__all__ = [
    "CONFIG",
    "DATA_INFO",
    "filter_part",
    "log",
    "rich",
    "json",
    "re",
    "Path",
    "duckdb",
    "plt",
    "np",
    "pd",
    "pn",
    "pa",
    "pc",
    "sm",
    "smf",
    "naturalsize",
    "metric",
    "show_df",
    "Markdown",
    "tabulate",
    "DEFAULTS",
    "label_memory",
    "scale_x_memory",
    "scale_y_memory",
    "scale_x_metric",
    "scale_y_metric",
    "load_sweep_iters",
    "load_sweep_result",
    "load_sweep_runs",
    "show_param_space",
]
