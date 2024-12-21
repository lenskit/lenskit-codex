import datetime as dt
from pathlib import Path

import structlog
from pydantic import ValidationError

from codex.runlog import CodexTask, RunLogDB, get_config

from . import collect

_log = structlog.stdlib.get_logger(__name__)


@collect.command("runlog")
def collect_runlog():
    "Collect run log entries into the main log files."
    log = _log.bind()
    cfg = get_config()
    rldb = RunLogDB()

    files = list(cfg.lobby_dir.glob("*.json"))
    log.info("collecting %d files from the lobby", len(files))
    integrated: list[Path] = []
    for tf in files:
        flog = log.bind(file=tf.as_posix())
        flog.debug("reading file")
        try:
            task = CodexTask.model_validate_json(tf.read_text())
        except IOError as e:
            flog.error("error reading file", exc_info=e)
            continue
        except ValidationError as e:
            flog.error("invalid task data", exc_info=e)
            continue

        if not task.start_time:
            flog.warning("task has no start time, skipping")
            continue

        date = dt.datetime.fromtimestamp(task.start_time)
        dbf = rldb.get_file(date)
        dbf.add_task(task)
        integrated.append(tf)

    rldb.save_all()

    for tf in integrated:
        _log.debug("removing integrated task", file=tf.as_posix())
        tf.unlink()

    _log.info("integrated %d task files from lobby", len(integrated))