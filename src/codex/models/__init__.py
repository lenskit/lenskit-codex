import json
import logging
from importlib import import_module
from inspect import Parameter, signature
from pathlib import Path
from typing import Protocol, cast

from lenskit.pipeline import Component
from pydantic import JsonValue

_log = logging.getLogger(__name__)


class ModelMod(Protocol):
    outputs: list[str]
    sweep_space: dict[str, list[int] | list[float] | list[str]]

    def default(self) -> Component: ...

    def from_config(self, *args, **kwargs) -> Component: ...


def model_module(name: str) -> ModelMod:
    mod = "codex.models." + name.replace("-", "_")
    _log.info("importing model module %s", mod)
    return cast(ModelMod, import_module(mod))


def load_model(name, config: str | Path) -> tuple[Component, dict[str, JsonValue]]:
    mod = model_module(name)
    if config == "default":
        _log.info("%s: using default config", name)
        return mod.default(), {}
    elif isinstance(config, Path):
        _log.info("%s: loading config from %s", name, config)
        params = json.loads(config.read_text())
        fc_sig = signature(mod.from_config)
        has_kw = any(p.kind == Parameter.VAR_KEYWORD for p in fc_sig.parameters.values())
        if not has_kw:
            params = {p: v for (p, v) in params.items() if p in fc_sig.parameters.keys()}
        return mod.from_config(**params), params
    else:
        _log.error("no valid model mode specified")
        raise RuntimeError("cannot load model")
