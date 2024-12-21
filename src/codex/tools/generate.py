import re
import sys
from collections.abc import Generator
from os import fspath
from pathlib import Path

import click
import structlog
from duckdb import connect
from humanize import naturalsize

from codex.cluster import ensure_cluster_init
from codex.collect import NDJSONCollector
from codex.data import TrainTestData, fixed_tt_data, partition_tt_data
from codex.inference import recommend_and_save
from codex.modelcfg import load_config
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.training import train_and_wrap_model

from . import codex

_log = structlog.stdlib.get_logger(__name__)


@codex.command("generate")
@click.option("--default", "config", help="use default configuration", flag_value="default")
@click.option("--param-file", "config", metavar="FILE", help="configure model from FILE")
@click.option(
    "-n",
    "--list-length",
    type=int,
    metavar="N",
    help="control recommendation list length",
    default=100,
)
@click.option("-o", "--output", type=Path, metavar="N", help="specify output database")
@click.option(
    "--ratings", "ratings_db", type=Path, help="second ratings file to go with main test DB"
)
@click.option("--test", "test_file", type=Path, help="database or Parquet file of test data")
@click.option(
    "--train",
    "train_files",
    type=Path,
    help="database or Parquet file of training data",
    multiple=True,
)
@click.option("--assignments", "assign_file", type=Path, help="database of test data assignments")
@click.option("--test-part", metavar="PARTS", help="test on specified part(s), train on others")
@click.argument("MODEL", required=True)
def generate(
    model: str,
    config: str | Path,
    output: Path,
    train_files: list[Path],
    list_length: int = 100,
    assign_file: Path | None = None,
    ratings_db: Path | None = None,
    test_file: Path | None = None,
    test_part: str | None = None,
):
    """
    Generate recommendations using a default or configured algorithm.
    """

    if config == "default":
        cfg_path = None
    else:
        cfg_path = Path(config)

    mod_cfg = load_config(model)

    if test_file:
        if assign_file or ratings_db or test_part:
            _log.error("--train/--test not compatible with alloc options")
            sys.exit(2)
        test_sets = fixed_test_sets(test_file, train_files)
    elif assign_file:
        if ratings_db is None:
            _log.error("must specify --ratings with --assignments")
            sys.exit(2)

        if not test_part:
            _log.error("must specify --test-part with --assignments")
            sys.exit(2)

        if test_file or train_files:
            _log.error("--train and --test incompatible with --assignments")
            sys.exit(2)

        test_sets = crossfold_test_sets(assign_file, ratings_db, test_part)

    ensure_cluster_init()

    output.mkdir(exist_ok=True, parents=False)
    (output / "training.json").unlink(missing_ok=True)
    (output / "inference.json").unlink(missing_ok=True)

    with (
        CodexTask(
            label=f"generate {model}", tags=["generate"], scorer=ScorerModel(name=model)
        ) as root_task,
        NDJSONCollector(output / "user-metrics.ndjson.zst") as metric_out,
    ):
        log = _log.bind(task_id=str(root_task.task_id))
        for part, data in test_sets:
            plog = log.bind(part=part)
            instance = mod_cfg.instantiate(cfg_path)
            plog.info("training model", name=instance.name, config=instance.params)
            with CodexTask(
                label=f"train {model}",
                tags=["train"],
                reset_hwm=True,
                scorer=ScorerModel(name=model, config=instance.params),
                data=DataModel(part=part),
            ) as task:
                pipe = train_and_wrap_model(
                    instance.scorer, data, predicts_ratings=mod_cfg.predictor, name=model
                )
            task.data.part = part

            plog.debug("run record: %s", task.model_dump_json(indent=2))
            plog.info(
                "finished in %.0fs (%.0fs CPU, %s peak RSS)",
                task.duration,
                task.cpu_time,
                naturalsize(task.peak_memory) if task.peak_memory else "unknown",
            )
            with open(output / "training.json", "a") as jsf:
                print(task.model_dump_json(), file=jsf)

            with data.open_db() as test_db:
                test = data.test_data(test_db)
                if len(test) == 0:
                    plog.error("no test data found")

            shard = f"part={part}"
            with CodexTask(
                label=f"recommend {model}",
                tags=["recommend"],
                reset_hwm=True,
                scorer=ScorerModel(name=model, config=instance.params),
                data=DataModel(part=part),
            ) as task:
                recommend_and_save(
                    pipe,
                    test,
                    list_length,
                    output / "recommendations" / shard,
                    output / "predictions" / shard if mod_cfg.predictor else None,
                    metric_out,
                    meta={"part": part},
                )

            with open(output / "inference.json", "a") as jsf:
                print(task.model_dump_json(), file=jsf)

        log.info("finished all parts")


def fixed_test_sets(test: Path, train: list[Path]) -> Generator[tuple[int, TrainTestData]]:
    # now figure out how to load things
    if test.suffix == ".parquet":
        # we should have training data, and no parts
        _log.info("using fixed test set %s", test)
        if not train:
            _log.error("must specify training data with test data")
        yield 0, fixed_tt_data(test, train)
    else:
        raise ValueError(f"unsupported test file {test}")


def crossfold_test_sets(
    assign: Path, ratings: Path, parts: str
) -> Generator[tuple[int, TrainTestData]]:
    with connect(fspath(assign), read_only=True) as db:
        db.execute(
            "SELECT DISTINCT partition FROM test_alloc",
        )
        all_parts = [r[0] for r in db.fetchall()]

    num_match = re.match(r"^(\d+)?-(\d+)", parts)
    if num_match:
        first = num_match.group(1)
        second = int(num_match.group(2))
        if first:
            test_parts = range(int(first), second + 1)
        else:
            test_parts = [p for p in all_parts if p != second]
    else:
        # FIXME: only supports integer parts
        test_parts = [int(p) for p in parts.split(",")]

    for part in test_parts:
        yield part, partition_tt_data(assign, ratings, part)
