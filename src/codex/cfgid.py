"""
Reproducible UUIDs from configuration points.
"""

from hashlib import sha512
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import JsonValue

NS_CONFIG = uuid5(NAMESPACE_URL, "https://ns.lenskit.org/config")


def config_id(config: dict[str, JsonValue]) -> UUID:
    h = sha512()
    _hash_object(config, h)
    return uuid5(NS_CONFIG, h.digest())


def _hash_object(data: JsonValue, h: Any):
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
        data.update(repr(data).encode() + b"\0")
