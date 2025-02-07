from __future__ import annotations

import datetime as dt
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class SplitSpec(BaseModel):
    source: str
    method: Literal["crossfold", "temporal"]
    version: int | str | None = None

    temporal: TemporalSpec | None = None
    crossfold: CrossfoldSpec | None = None
    holdout: HoldoutSpec | None = None


class TemporalSpec(BaseModel):
    """
    Configuration for a global temporal split.
    """

    tune: dt.date
    test: dt.date
    min_train: int | None = None


class CrossfoldSpec(BaseModel):
    method: Literal["users"]
    partitions: int


class HoldoutSpec(BaseModel):
    selection: Literal["random"]
    count: int


def load_split_spec(path: Path) -> SplitSpec:
    text = path.read_text()
    data = tomllib.loads(text)
    return SplitSpec.model_validate(data)
