import logging
from importlib import import_module

_log = logging.getLogger(__name__)


def model_module(name: str):
    mod = "codex.models." + name.replace("-", "_")
    _log.info("importing mdel module %s", mod)
    return import_module(mod)
