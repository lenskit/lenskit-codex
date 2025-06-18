"""
Codex CLI tools.
"""

import logging
import os

import click

from ..runlog import configure


@click.group("codex")
def codex():
    "LensKit codex tools"
    configure()
    logging.getLogger("ray").setLevel(logging.DEBUG)
    os.environ["RAY_AIR_NEW_OUTPUT"] = "0"


from . import (  # noqa: F401, E402
    collect,
    duckscript,
    generate,
    movielens,
    runlog,
    search,
    split,
    test_measure,
    trec,
)
