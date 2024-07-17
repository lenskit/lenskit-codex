"""
Split ratings / interaction data for evaluation.

Usage:
    split.py [-v] SPEC

Options:
    -v, --verbose       enable verbose logging
    SPEC                path to split specification TOML file
"""

import logging
from pathlib import Path

from docopt import docopt
from sandal import autoroot  # noqa: F401
from sandal.cli import setup_logging

from codex.splitting.spec import load_split_spec

_log = logging.getLogger("codex.split")


def main():
    opts = docopt(__doc__)
    setup_logging(opts["--verbose"])

    path = Path(opts["SPEC"])
    _log.info("loading spec from %s", path)
    split = load_split_spec(Path(opts["SPEC"]))
    _log.debug("loaded split config: %s", split)


if __name__ == "__main__":
    main()
