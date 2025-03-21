from os import PathLike
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent


def codex_root() -> Path:
    """
    Get the root directory of the codex.
    """
    assert (ROOT_DIR / "pixi.toml").exists()
    return ROOT_DIR


def codex_relpath(path: str | PathLike[str]) -> Path:
    path = Path(path)
    resolved = path.absolute()
    root = codex_root()
    return resolved.relative_to(root)
