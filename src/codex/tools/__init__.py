"""
Codex CLI tools.
"""

import os

import click

from .. import runlog


@click.group("codex")
def codex():
    "LensKit codex tools"
    runlog.configure()
    os.environ["RAY_AIR_NEW_OUTPUT"] = "0"


from . import (  # noqa: F401, E402
    amazon,
    collect,
    debug,
    duckscript,
    generate,
    movielens,
    search,
    split,
    test_measure,
    trec,
)
