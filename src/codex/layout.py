from pathlib import Path

from pyprojroot import find_root, has_file


def codex_root() -> Path:
    """
    Get the root directory of the codex.
    """
    return find_root(has_file("pixi.toml"))
