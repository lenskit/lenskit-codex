from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Annotated, Literal, NamedTuple, Union

import structlog
from lenskit.pipeline import Component
from lenskit.pipeline.types import parse_type_string
from numpy.random import Generator
from pydantic import BaseModel, Field
from pyprojroot import find_root, has_file
from scipy import stats

_log = structlog.get_logger(__name__)

type ModelParam = float | int | str | tuple[float, ...] | tuple[str, ...]
type ModelParams = dict[str, ModelParam]


class ModelInstance(NamedTuple):
    name: str
    scorer: Component
    params: ModelParams
    config: ModelConfig


class CategorialParamSpace(BaseModel, extra="forbid"):
    type: Literal["categorical"] = "categorical"
    values: list[str]

    def choose(self, rng: Generator) -> ModelParam:
        return rng.choice(self.values)


class NumericParamSpace(BaseModel, extra="forbid"):
    type: Literal["integer", "real"] = "real"
    "The parameter's type."
    min: int | float
    "The parameter's minimum value."
    max: int | float
    "The parameter's maximum value."
    space: Literal["linear", "logarithmic"] = "linear"
    "The space on which to sample the parameter."
    tuple: int | None = None
    "Generate a tuple instead of a single value."

    def choose(self, rng: Generator, *, _single=False) -> ModelParam:
        if self.tuple and not _single:
            return tuple([self.choose(rng, _single=True) for _i in range(self.tuple)])  # type: ignore

        if self.space == "linear":
            if self.type == "integer":
                dist = stats.randint(self.min, self.max)
                return dist.rvs(random_state=rng)
            else:
                dist = stats.uniform(self.min, self.max)
                return dist.rvs(random_state=rng)
        else:
            shift = 0
            if self.min == 0:
                dist = stats.loguniform(self.min + 1e-6, self.max + 1e-6)
                shift = 1e-6
            else:
                dist = stats.loguniform(self.min, self.max)
            val = dist.rvs(random_state=rng) - shift
            if self.type == "integer":
                val = round(val)
            return val


class SearchConfig(BaseModel, extra="forbid"):
    "Configuration for parameter search."

    random_points: int = 100
    "Number of random points to search"

    grid: ModelParams | None = None
    params: (
        dict[
            str,
            Annotated[Union[CategorialParamSpace, NumericParamSpace], Field(discriminator="type")],
        ]
        | None
    ) = None


class ModelConfig(BaseModel, extra="forbid"):
    name: str | None = None
    scorer: str
    enabled: bool = True
    predictor: bool = False

    constant: ModelParams = {}
    default: ModelParams = {}
    search: SearchConfig = Field(default_factory=SearchConfig)

    @property
    def scorer_class(self) -> type[Component]:
        return parse_type_string(self.scorer)

    def instantiate(self, config: os.PathLike[str] | ModelParams | None = None) -> ModelInstance:
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
