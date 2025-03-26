import json
import logging
import warnings
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotnine as pn
import pyarrow as pa
import pyarrow.compute as pc
import tqdm
from IPython.display import Markdown
from itables import show as show_df
from lenskit.logging import get_logger
from rich.console import Console
from tabulate import tabulate

from .data import DATA_INFO
from .plots import DEFAULTS, label_memory, scale_x_memory, scale_y_memory
from .sweep import load_sweep_iters, load_sweep_result, load_sweep_runs, show_param_space

warnings.filterwarnings("ignore", "IProgress not found", tqdm.TqdmWarning)
logging.getLogger("ray.widgets").setLevel(logging.ERROR)

log = get_logger("notebook")
rich = Console()

__all__ = [
    "DATA_INFO",
    "log",
    "rich",
    "json",
    "Path",
    "duckdb",
    "plt",
    "np",
    "pd",
    "pn",
    "pa",
    "pc",
    "show_df",
    "Markdown",
    "tabulate",
    "DEFAULTS",
    "label_memory",
    "scale_x_memory",
    "scale_y_memory",
    "load_sweep_iters",
    "load_sweep_result",
    "load_sweep_runs",
    "show_param_space",
]
