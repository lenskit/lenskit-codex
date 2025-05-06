"""
RNG utilities.
"""

from __future__ import annotations

import tomllib

from pydantic import BaseModel

from .layout import codex_root

_config: CodexConfig | None = None


def get_config() -> CodexConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def load_config() -> CodexConfig:
    cfg_file = codex_root() / "config.toml"
    cfg_data = tomllib.loads(cfg_file.read_text())
    return CodexConfig.model_validate(cfg_data)


class RandomConfig(BaseModel):
    seed: int


class TuningConfig(BaseModel):
    points: int
    default: bool = False


class PowerConfig(BaseModel):
    co2e_rate: float | None = None


class CodexConfig(BaseModel, extra="allow"):
    random: RandomConfig
    tuning: dict[str, TuningConfig] = {}
    power: PowerConfig = PowerConfig()
