from lenskit.logging import get_logger

from codex.runlog import human_power, power_metrics

from .. import codex

_log = get_logger(__name__)


@codex.group("debug")
def debug():
    pass


@debug.command("power")
def debug_power():
    for pt in ["chassis", "cpu", "gpu"]:
        value = power_metrics(pt + "_power", 60.0)
        if value is None:
            _log.warning("%s power not available", pt)
        else:
            _log.info("%s power: %s", pt, human_power(value))
