"""
Codex CLI tools.
"""

import click

from .. import runlog


@click.group("codex")
def codex():
    "LensKit codex tools"
    runlog.configure()


from . import (  # noqa: F401, E402
    amazon,
    collect,
    duckscript,
    generate,
    movielens,
    split,
    sweep,
    test_measure,
    trec,
)
