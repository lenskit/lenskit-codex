from os import PathLike
from pathlib import Path

from pyprojroot import find_root, has_file


def codex_root() -> Path:
    """
    Get the root directory of the codex.
    """
    return find_root(has_file("pixi.toml"))


def codex_relpath(path: str | PathLike[str]) -> Path:
    path = Path(path)
    resolved = path.absolute()
    root = codex_root()
    return resolved.relative_to(root)
