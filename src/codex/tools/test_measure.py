import time

import click
import structlog
from humanize import metric

from codex.runlog import CodexTask

from . import codex

_log = structlog.stdlib.get_logger(__name__)


@codex.command("test-measurements")
@click.option(
    "-s",
    "--sleep",
    type=float,
    metavar="SECS",
    help="task time to sleep",
    default=2.5,
)
def test_measurements(sleep):
    _log.info("starting test task", duration=sleep)
    with CodexTask("test", tags=["test"]) as task:
        time.sleep(sleep)

    _log.info("completed task %s", task.task_id)
    _log.info("duration: %.2fs", task.duration)
    _log.info(
        "power consumption: %s CPU, %s chassis",
        metric(task.cpu_power, "J") if task.cpu_power else "NA",
        metric(task.system_power, "J") if task.system_power else "NA",
    )
