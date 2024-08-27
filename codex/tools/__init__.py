"""
Codex CLI tools.
"""

import click
from sandal.cli import setup_logging

from .amazon import amazon  # noqa: F401


@click.group("codex-tool")
@click.option("-v", "--verbose")
def run(verbose: bool = False):
    setup_logging(verbose)


run.add_command(amazon)
