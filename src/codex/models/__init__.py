from collections.abc import Iterable
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

from lenskit.logging import get_logger
from lenskit.parallel import get_parallel_config
from lenskit.pipeline import Component
from pydantic import JsonValue, TypeAdapter

_log = get_logger(__name__)
model_dir = Path(__file__).parent


class ModelAdapter(Protocol):
    """
    Adapters for reusing a base model across tuning, where the model's trained
    state does not change between tunings.
    """

    def base_model(self) -> Component: ...
    def adapt_model(self, base, config) -> Component: ...


class ModelDef:
    """
    Encapsulation of a Python module defining a model for search.
    """

    name: str
    "The name of the model specification (kebab case)."

    module: ModuleType

    def __init__(self, name, module):
        self.name = name
        self.module = module

    @property
    def module_name(self) -> str:
        """
        The module name (snake case).
        """
        return self.name.replace("-", "_")

    @property
    def scorer_class(self) -> type[Component]:
        return self.module.SCORER

    @property
    def config_class(self):
        return self.scorer_class.config_class()

    @property
    def default_config(self):
        return getattr(self.module, "DEFAULT_CONFIG", {})

    @property
    def static_config(self):
        return getattr(self.module, "STATIC_CONFIG", {})

    @property
    def is_predictor(self) -> bool:
        return getattr(self.module, "PREDICTOR", False)

    @property
    def search_space(self) -> dict[str, Any]:
        return getattr(self.module, "SEARCH_SPACE", {})

    @property
    def tuning_cpus(self) -> int:
        config = get_parallel_config()
        match getattr(self.module, "TUNE_CPUS", None):
            case None:
                return config.threads
            case "all":
                return config.total_threads
            case n:
                return n

    @property
    def options(self) -> dict[str, JsonValue]:
        return getattr(self.module, "OPTIONS", {})

    def instantiate(self, params: dict[str, Any] | None = None):
        """
        Instantiate a model with  specified parameters.
        """
        log = _log.bind(name=self.name)

        static = self.static_config
        if not isinstance(static, dict):
            static = TypeAdapter(self.config_class).dump_python(static)
        if static:
            log.debug("found static configuration", config=static)

        config = static.copy()
        if params is not None:
            log.debug("applying configuration", config=params)
            config.update(params)
        else:
            config = self.default_config
            if not isinstance(config, dict):
                config = TypeAdapter(self.config_class).dump_python(config)
            log.debug("using default configuration", config=config)

        mod_cls = self.scorer_class
        log.debug("instantiating model", config=config, component=mod_cls)

        model = mod_cls(**config)
        log.info("instantiated model", model=model)
        return model


def discover_models() -> Iterable[str]:
    """
    Discover the available model configuration names.
    """
    for mf in model_dir.glob("*.py"):
        if not mf.name.startswith("_"):
            yield mf.stem.replace("_", "-")


def load_model(name: str) -> ModelDef:
    """
    Load a model's definition.
    """
    name = name.replace("_", "-").lower()
    fname = name.replace("-", "_")

    _log.info("importing model module", module=fname)
    module = import_module(f"codex.models.{fname}")
    return ModelDef(name, module)
