"""
Codex CLI tools.
"""

from pathlib import Path

import click
import seedbank
from sandal.cli import setup_logging

root = Path(__file__).parent.parent.parent


@click.group("codex-tool")
@click.option("-v", "--verbose")
def codex(verbose: bool = False):
    setup_logging(verbose)
    seedbank.init_file(root / "config.toml")


from . import (  # noqa: F401, E402
    amazon,
    generate,
)
