"""
Codex CLI tools.
"""

import logging
from pathlib import Path

import click
import seedbank
from sandal.cli import setup_logging

root = Path(__file__).parent.parent.parent


@click.group("codex-tool")
@click.option("-v", "--verbose", is_flag=True, help="enable debug logging output")
def codex(verbose: bool = False):
    setup_logging(verbose)
    logging.getLogger("numba").setLevel(logging.INFO)
    seedbank.init_file(root / "config.toml")


from . import (  # noqa: F401, E402
    amazon,
    collect,
    duckscript,
    generate,
    movielens,
    split,
    sweep,
    trec,
)
