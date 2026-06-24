#!/usr/bin/env python
"""
Convert a data structure to Tcl-compatible format.

Usage:
    parse-to-tcl.py [-v] [--header] -f FMT --stdin
    parse-to-tcl.py [-v] [--header] [-f FMT] FILE
    parse-to-tcl.py [-v] --all-headers

Options:
    -v, --verbose
        Enable verbose logging.
    -f FMT, --format=FMT
        Parse in format FMT (toml, yaml, json).
    --header
        Parse the markup header of a document.
    --all-headers
        Parse markup headers of all QMD files.
    --indent
        Write indented output.
    --stdin
        Parse standard input.
    FILE
        The file to load and parse.
"""

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

from docopt import docopt
from lenskit.logging import LoggingConfig, get_logger
from ruamel.yaml import YAML

_log = get_logger("parse-to-tcl")


def main():
    opts = docopt(__doc__ or "")
    lc = LoggingConfig()
    if opts["--verbose"]:
        lc.set_verbose(True)
    lc.apply()

    fmt = opts["--format"]
    file = opts["FILE"]
    if file is not None:
        file = Path(file)

    if fmt is None:
        if opts["--header"] or opts["--all-headers"]:
            fmt = "yaml"
        else:
            assert file is not None
            _log.debug("guessing file type from %s", file)
            fmt = file.suffix[1:]

    if opts["--all-headers"]:
        data = {}
        for path in Path(".").glob("**/*.qmd"):
            if re.match(r"^(.*/)?[_.].*", path.as_posix()):
                continue

            _log.info("reading %s", path)
            with path.open("rt") as df:
                data[path.as_posix()] = parse_header(df, "yaml", file=path.as_posix())
    else:
        if opts["--stdin"]:
            reader = sys.stdin
        else:
            assert file is not None
            _log.debug("opening input %s", file)
            reader = open(file, "rb")

        _log.debug("parsing data from input")
        if opts["--header"]:
            data = parse_header(reader, fmt, file=file)
        else:
            data = read_and_parse(reader, fmt)

    _log.debug("writing data to TCL format")
    write_tcl(data, level=-1)


def read_and_parse(src, fmt):
    match fmt:
        case "toml":
            _log.debug("parsing toml")
            return tomllib.load(src)
        case "yaml" | "yml":
            _log.debug("parsing yaml")
            yaml = YAML(typ="safe")
            return yaml.load(src)
        case "json":
            _log.debug("parsing json")
            return json.load(src)
        case _:
            raise ValueError(f"unsupported format {fmt}")


def parse_header(src, fmt, file):
    text = None
    for lno, line in enumerate(src, 1):
        if text is None:
            if line == "---\n":
                text = ""
            else:
                _log.warn("expected header line ---", file=file)
                return {}
        elif line == "---\n":
            _log.debug("finished header on line %d", lno)
            break
        else:
            text += line + "\n"

    assert text is not None
    match fmt:
        case "toml":
            return tomllib.loads(text)
        case "yaml" | "yml":
            yaml = YAML(typ="safe")
            return yaml.load(text)
        case "json":
            return json.loads(text)
        case _:
            raise ValueError(f"unsupported format {fmt}")


def write_tcl(data: Any, *, level: int = 0, prefix: bool = True, eol: str = "\n"):
    """
    Write a JSON-compatible data structure in Tcl format.
    """
    leader = " " * max(level, 0) * 2

    if prefix:
        print(leader, end="")

    if isinstance(data, list):
        if level >= 0:
            print("{")
        for obj in data:
            write_tcl(obj, level=level + 1)
        if level >= 0:
            print(leader + "}", end=eol)
    elif isinstance(data, dict):
        if level >= 0:
            print("{")
        for key, value in data.items():
            write_tcl(key, eol=" ", level=level + 1)
            write_tcl(value, level=level + 1, prefix=False)
        if level >= 0:
            print(leader + "}", end=eol)
    elif isinstance(data, str):
        if not re.match(r"^[\w_@!%^/.*-]+$", data):
            data = re.sub(r"[{}\\]", "\\$0", data)
            data = "{" + data + "}"
        print(data, end=eol)
    elif isinstance(data, bool):
        print(int(data), end=eol)
    else:
        write_tcl(str(data), level=level, prefix=False, eol=eol)


if __name__ == "__main__":
    main()
