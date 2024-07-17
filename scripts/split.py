"""
Split ratings / interaction data for evaluation.

Usage:
    split.py [-v] SPEC

Options:
    -v, --verbose       enable verbose logging
    SPEC                path to split specification TOML file
"""

import logging

from docopt import docopt
from sandal import autoroot  # noqa: F401
from sandal.cli import setup_logging

_log = logging.getLogger("codex.split")


def main():
    opts = docopt(__doc__)
    setup_logging(opts["--verbose"])


if __name__ == "__main__":
    main()
