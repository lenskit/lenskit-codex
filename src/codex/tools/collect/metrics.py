from collections.abc import Generator
from pathlib import Path

import click
import pandas as pd
import structlog

from codex.runlog import CodexTask

from . import collect

_log = structlog.stdlib.get_logger(__name__)
_run_base = Path("runs")


@collect.command("metrics")
@click.option("-S", "--summary-output", metavar="FILE", type=Path, help="Summary output file.")
@click.option("-U", "--user-output", metavar="FILE", type=Path, help="User-level output file.")
@click.option("-L", "--run-list", type=Path, metavar="FILE", help="Load run list from FILE.")
def collect_metrics(summary_output: Path, user_output: Path, run_list: Path):
    "Collect metrics from runs for a data set."
    _log.debug("reading run list")
    runs = pd.read_csv(run_list)
    runs = runs.set_index("path").astype("category")

    _log.info("collecting metrics from %d runs", len(runs))
    user_metrics = {path: _collect_user_metrics(_run_base / path) for path in runs.index}
    metric_df = pd.concat(user_metrics, names=["path"])
    summaries = (
        metric_df.drop(columns=["user_id"])
        .astype({"part": "str"})
        .groupby(["path", "part"])
        .agg("mean")
    )

    metric_df = runs.join(metric_df)

    _log.info("saving user-level metrics output", file=str(user_output))
    metric_df.to_parquet(user_output, index=False, compression="zstd")

    times = pd.concat(_collect_run_metrics(path) for path in runs.index)
    summary_df = runs.join(times)
    summary_df = summary_df.join(summaries)
    summary_df = summary_df.reset_index("part")
    _log.info("saving summary metrics output", file=str(summary_output))
    summary_df.to_csv(summary_output, index=False)


def _collect_user_metrics(path: Path) -> pd.DataFrame:
    _log.debug("reading user metrics", path=str(path))
    return pd.read_json(path / "user-metrics.ndjson.zst", lines=True)


def _collect_run_metrics(path: str) -> pd.DataFrame:
    train_tasks = {task.data.part: task for task in _read_tasks(_run_base / path / "training.json")}
    infer_tasks = {
        task.data.part: task for task in _read_tasks(_run_base / path / "inference.json")
    }

    points = []
    for part in train_tasks.keys():
        train = train_tasks[part]
        infer = infer_tasks[part]
        points.append(
            {
                "path": path,
                "part": part,
                "train_task": train.task_id,
                "infer_task": infer.task_id,
                "train_time": train.duration,
                "train_cpu": train.cpu_time,
                "train_power": train.chassis_power,
                "train_mem": train.peak_memory,
                "train_gmem": train.peak_gpu_memory,
                "infer_time": infer.duration,
                "infer_cpu": infer.cpu_time,
                "infer_power": infer.chassis_power,
            }
        )

    return pd.DataFrame.from_records(points).set_index(["path", "part"])


def _read_tasks(path: Path) -> Generator[CodexTask, None, None]:
    with path.open("r") as tf:
        for line in tf:
            yield CodexTask.model_validate_json(line)
