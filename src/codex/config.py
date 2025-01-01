"""
RNG utilities.
"""

from __future__ import annotations

import tomllib
from binascii import crc32

from numpy.random import SeedSequence
from pydantic import BaseModel

from .layout import codex_root


def load_config() -> CodexConfig:
    cfg_file = codex_root() / "config.toml"
    cfg_data = tomllib.loads(cfg_file.read_text())
    return CodexConfig.model_validate(cfg_data)


def rng_seed(*keys: str | int | bytes | None) -> SeedSequence:
    """
    Get the random seed.

    Args:
        keys:
            Additional data to append to the configured RNG seed, to specialize
            the seed different models, runs, etc.  String are converted to key
            elements by their CRC32 checksum.
    """
    cfg = load_config()
    seed = [cfg.random.seed]
    for k in keys:
        if isinstance(k, str):
            k = k.encode("utf8")
        if k is None:
            seed.append(0)
        elif isinstance(k, int):
            seed.append(k)
        else:
            seed.append(crc32(k))
    return SeedSequence(seed)


class CodexConfig(BaseModel, extra="allow"):
    random: RandomConfig


class RandomConfig(BaseModel):
    seed: int
