#!/usr/bin/env python3
"""
Re-render the project's generated structure.

Usage:
    rerender.py [options]

Options:
    -v, --verbose       use verbose logging output
"""

import json
import logging
from os import fspath
from pathlib import Path
from typing import Any

from _jsonnet import evaluate_file
from docopt import docopt
from sandal import autoroot  # noqa: F401
from sandal.cli import setup_logging
from sandal.project import project_root
from yaml import safe_dump

_log = logging.getLogger("codex.rerender")


def main(options):
    root = project_root()

    render_pipeline(options, root)


def render_pipeline(options, root: Path):
    specs = root.glob("**/dvc.jsonnet")
    for jnf in specs:
        jnf = jnf.relative_to(root)
        _log.info("evaluting %s", jnf)
        results = evaluate_file(fspath(jnf))
        results = json.loads(results)
        if "subdirs" in results:
            _log.debug("scanning subdirectories")
            for name, pipe in results["subdirs"].items():
                _log.debug("found subdir %s", name)
                save_pipeline(pipe, jnf.parent / name)
            del results["subdirs"]
        save_pipeline(results, jnf.parent)


def save_pipeline(pipe: dict[str, Any], dir: Path):
    file = dir / "dvc.yaml"
    _log.info("saving %s", file)
    with file.open("wt") as pf:
        safe_dump(pipe, pf)


if __name__ == "__main__":
    args = docopt(__doc__)
    setup_logging(args["--verbose"])
    main(args)
