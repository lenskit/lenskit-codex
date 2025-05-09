"""
RNG utilities.
"""

from __future__ import annotations

import tomllib
from fnmatch import fnmatch

from deepmerge import always_merger
from lenskit.logging import get_logger
from pydantic import BaseModel

from .layout import codex_root

_log = get_logger(__name__)

_config: CodexConfig | None = None

CONFIG_FILES = {"config.toml": True, "config.local.toml": False}


def get_config() -> CodexConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def load_config() -> CodexConfig:
    config = {}
    root = codex_root()
    for file, warn in CONFIG_FILES.items():
        path = root / file
        if path.exists():
            _log.debug("reading configuration", file=file, dir=str(root))
            cfg = tomllib.loads(path.read_text())
            config = always_merger.merge(config, cfg)
        elif warn:
            _log.warning("configuration file %s not found", file, dir=str(root))
        else:
            _log.debug("configuration file not found", file=file, dir=str(root))

    return CodexConfig.model_validate(config)


class RandomConfig(BaseModel):
    seed: int


class TuningConfig(BaseModel):
    points: int
    default: bool = False


class PowerConfig(BaseModel):
    co2e_rate: float | None = None
    "The CO2 equivalency rate (in kgCO2 / MWh)."
    prometheus_url: str | None = None
    "URL for Prometheus endpoint."


class MachineConfig(BaseModel):
    idle_watts: float | None = None
    "Idle power draw (in watts)."

    power_queries: dict[str, str] = {}
    "Prometheus queries for power draw."


class ModelRule(BaseModel):
    model: str
    data: str

    def matches_model(self, model: str):
        return fnmatch(model, self.model)


class ModelConfig(BaseModel):
    """
    Model configuration rules.
    """

    include: list[ModelRule] = []


class CodexConfig(BaseModel, extra="allow"):
    random: RandomConfig
    machine: str | None = None
    tuning: dict[str, TuningConfig] = {}
    models: ModelConfig = ModelConfig()
    power: PowerConfig = PowerConfig()
    machines: dict[str, MachineConfig] = {}

    @property
    def machine_config(self) -> MachineConfig:
        if self.machine is not None:
            if machine := self.machines.get(self.machine, None):
                return machine

        return MachineConfig()
