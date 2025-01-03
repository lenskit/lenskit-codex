"""
Reproducible UUIDs from configuration points.
"""

from __future__ import annotations

from hashlib import sha512
from typing import Any, Mapping, Sequence
from uuid import NAMESPACE_URL, UUID, uuid5

NS_CONFIG = uuid5(NAMESPACE_URL, "https://ns.lenskit.org/config")

type ConfigData = None | str | float | int | bool | Sequence[ConfigData] | Mapping[str, ConfigData]
"""
Extension of :class:`pydantic.JsonValue` for tuples.
"""


def config_id(config: dict[str, ConfigData]) -> UUID:
    h = sha512()
    _hash_object(config, h)
    return uuid5(NS_CONFIG, h.hexdigest())


def _hash_object(data: ConfigData, h: Any):
    if isinstance(data, dict):
        h.update(f"MAP\0{len(data)}\0".encode())
        for k in sorted(data.keys()):
            h.update(k.encode() + b"\0")
            _hash_object(data[k], h)
    elif isinstance(data, (list, tuple)):
        h.update(f"ARRAY\0{len(data)}\0".encode())
        for obj in data:
            _hash_object(obj, h)
    elif isinstance(data, (str, int, float, bool)):
        h.update(str(data).encode() + b"\0")
    elif data is None:
        h.update(b"\0")
    else:
        h.update(repr(data).encode() + b"\0")
