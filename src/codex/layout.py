from os import PathLike
from pathlib import Path

import yaml
from pydantic import BaseModel

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


class DataSetInfo(BaseModel):
    """
    Information for a data set.
    """

    name: str = "UNNAMED"
    models: list[str] = []
    splits: list[str] = []
    searches: list[str] = []

    @property
    def default_split(self) -> str:
        if len(self.splits) != 1:
            raise RuntimeError("no default split")
        else:
            return self.splits[0]


def load_data_info(path: str | Path | None = None):
    """
    Load dataset info.
    """
    if path is None:
        path = Path()
    else:
        path = Path(path)

    with open(path / "dataset.yml", "rt") as yf:
        data = yaml.safe_load(yf)
    return DataSetInfo.model_validate(data)
