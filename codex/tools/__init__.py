"""
Codex CLI tools.
"""

import logging

import click
import seedbank
from sandal.cli import setup_logging
from sandal.project import project_root
from xshaper import configure

root = project_root()


@click.group("codex-tool")
@click.option("-v", "--verbose", is_flag=True, help="enable debug logging output")
def codex(verbose: bool = False):
    setup_logging(verbose)
    logging.getLogger("numba").setLevel(logging.INFO)
    seedbank.init_file(root / "config.toml")
    configure(root / "run-log")


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
