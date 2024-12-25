from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import NamedTuple

import structlog
from lenskit.pipeline import Component
from lenskit.pipeline.types import parse_type_string
from pydantic import BaseModel, JsonValue
from pyprojroot import find_root, has_file

_log = structlog.get_logger(__name__)


class ModelInstance(NamedTuple):
    name: str
    scorer: Component
    params: dict[str, JsonValue]
    config: ModelConfig


class ModelConfig(BaseModel, extra="forbid"):
    name: str | None = None
    scorer: str
    enabled: bool = True
    predictor: bool = False

    constant: dict[str, JsonValue] = {}
    default: dict[str, JsonValue] = {}
    sweep: dict[str, list[JsonValue]] | None = None

    @property
    def scorer_class(self) -> type[Component]:
        return parse_type_string(self.scorer)

    def instantiate(
        self, config: os.PathLike[str] | dict[str, JsonValue] | None = None
    ) -> ModelInstance:
        """
        Instantiate the configured model.
        """
        log = _log.bind(model=self.name)
        params = self.constant

        if config is None:
            log.info("instantiating with default parameters")
            params = params | self.default
        elif isinstance(config, dict):
            log.info("instantiating with provided parameters")
            params = params | config
        else:
            path = Path(config)
            log = log.bind(file=str(config))
            _log.info("reading parameters from file")
            if path.suffix == ".json":
                with open(config) as jsf:
                    fdata = json.load(jsf)
            elif path.suffix == ".toml":
                with open(config, "rb") as inf:
                    fdata = tomllib.load(inf)
            else:
                raise ValueError(f"unsupported file type for {path}")

            if "params" in fdata:
                log.debug("using params object")
                fdata = fdata["params"]
            params = params | fdata

        cls = self.scorer_class
        scorer = cls.from_config(params)
        return ModelInstance(self.name or cls.__name__, scorer, params, self)


def load_config(name: str):
    """
    Get a model configuration.
    """
    root = find_root(has_file("pixi.lock"))

    cfg_file = root / "models" / f"{name}.toml"
    data = tomllib.loads(cfg_file.read_text())
    cfg = ModelConfig.model_validate(data)
    cfg.name = cfg_file.stem
    return cfg
