import logging
from importlib import import_module
from typing import Protocol, cast

from lenskit.algorithms import Algorithm

_log = logging.getLogger(__name__)


class AlgoMod(Protocol):
    outputs: list[str]
    sweep_space: dict[str, list[int] | list[float] | list[str]]

    def default(self) -> Algorithm: ...

    def from_config(self, *args, **kwargs) -> Algorithm: ...


def model_module(name: str) -> AlgoMod:
    mod = "codex.models." + name.replace("-", "_")
    _log.info("importing mdel module %s", mod)
    return cast(AlgoMod, import_module(mod))
