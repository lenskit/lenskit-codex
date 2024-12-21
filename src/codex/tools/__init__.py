"""
Codex CLI tools.
"""

import logging

import click
from lenskit.logging import LoggingConfig

from .. import runlog


@click.group("codex-tool")
@click.option("-v", "--verbose", is_flag=True, help="enable debug logging output")
def codex(verbose: bool = False):
    lc = LoggingConfig()
    if verbose:
        lc.set_verbose()

    lc.apply()
    logging.getLogger("numba").setLevel(logging.INFO)
    runlog.configure()


from . import (  # noqa: F401, E402
    amazon,
    collect,
    duckscript,
    generate,
    movielens,
    split,
    # sweep,
    test_measure,
    trec,
)
