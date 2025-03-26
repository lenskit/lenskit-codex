"""
RNG utilities.
"""

from __future__ import annotations

import tomllib

from pydantic import BaseModel

from .layout import codex_root


def load_config() -> CodexConfig:
    cfg_file = codex_root() / "config.toml"
    cfg_data = tomllib.loads(cfg_file.read_text())
    return CodexConfig.model_validate(cfg_data)


class CodexConfig(BaseModel, extra="allow"):
    random: RandomConfig


class RandomConfig(BaseModel):
    seed: int
