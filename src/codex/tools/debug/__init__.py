import click
from lenskit.logging import get_logger, stdout_console

from codex.config import load_config
from codex.runlog import human_power, power_metrics

from .. import codex

_log = get_logger(__name__)


@codex.group("debug")
def debug():
    pass


@debug.command("config")
@click.option("--machine", is_flag=True)
def debug_config(machine: bool):
    "Dump configuration object."
    console = stdout_console()
    config = load_config()
    if machine:
        console.print(config.machine_config)
    else:
        console.print_json(config.model_dump_json())


@debug.command("power")
def debug_power():
    for pt in ["chassis", "cpu", "gpu"]:
        value = power_metrics(pt, 60.0)
        if value is None:
            _log.warning("%s power not available", pt)
        else:
            _log.info("%s power: %s", pt, human_power(value))
