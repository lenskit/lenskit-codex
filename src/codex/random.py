"""
Management for LensKit Codex randomness.

This manages NumPy generators with a fixed root seed, and deriving additional
seeds based on the program name and the specific action, so different models
start with different seeds.
"""

from binascii import crc32

from lenskit.config import lenskit_config
from numpy.random import SeedSequence


def rng_seed(*keys: str | int | bytes | None) -> SeedSequence:
    """
    Get a random seed.

    Args:
        keys:
            Additional data to append to the configured RNG seed, to specialize
            the seed different models, runs, etc.  String are converted to key
            elements by their CRC32 checksum.
    """
    cfg = lenskit_config()
    seed = SeedSequence(cfg.random.seed)
    if keys:
        seed = extend_seed(seed, *keys)
    return seed


def extend_seed(seed: SeedSequence, *keys: str | int | bytes | None) -> SeedSequence:
    spawns = list(seed.spawn_key)

    for k in keys:
        if isinstance(k, str):
            k = k.encode("utf8")
        if k is None:
            spawns.append(0)
        elif isinstance(k, int):
            spawns.append(k)
        else:
            spawns.append(crc32(k))

    # we kinda abuse the spawn key
    return SeedSequence(seed.entropy, spawn_key=spawns)


def int_seed(seed: SeedSequence) -> int:
    return seed.generate_state(1)[0]
