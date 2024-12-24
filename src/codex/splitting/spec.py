from __future__ import annotations

import datetime as dt
import tomllib
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel


class SplitSpec(BaseModel):
    source: str
    method: Literal["crossfold"]

    temporal: Optional[TemporalSpec]
    crossfold: Optional[CrossfoldSpec]
    holdout: Optional[HoldoutSpec]


class TemporalSpec(BaseModel):
    """
    Configuration for a global temporal split.
    """

    valid: dt.date
    test: dt.date


class CrossfoldSpec(BaseModel):
    method: Literal["users"]
    partitions: int
    assign_db: str


class HoldoutSpec(BaseModel):
    selection: Literal["random"]
    count: int


def load_split_spec(path: Path) -> SplitSpec:
    text = path.read_text()
    data = tomllib.loads(text)
    return SplitSpec.model_validate(data)
