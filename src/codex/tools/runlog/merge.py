from pathlib import Path

import click
import structlog

from codex.runlog import RunLogDB, RunLogDBFile

from . import runlog

_log = structlog.stdlib.get_logger(__name__)


@runlog.command("merge")
@click.argument("file", type=Path, required=True)
def merge_runlog(file: Path):
    "Merge run log entries from a log file into the main log files."
    log = _log.bind(file=str(file))
    rldb = RunLogDB()

    log.info("loading log entries")
    indb = RunLogDBFile.read_db(file)
    log = log.bind(n=len(indb.log_entries))
    log.info("incorporating log entries")
    for task in indb.log_entries.values():
        rldb.add_task(task)

    log.info("saving merged log")
    rldb.save_all()

    log.info("merge complete")
