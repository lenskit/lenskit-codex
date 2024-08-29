import logging
import re
import sys
from collections.abc import Generator
from os import fspath
from pathlib import Path

import click
import duckdb
from duckdb import connect
from humanize import naturalsize
from lenskit.algorithms import Recommender

from codex.data import TrainTestData, fixed_tt_data, partition_tt_data
from codex.inference import connect_cluster, run_recommender
from codex.models import load_model, model_module
from codex.results import create_result_tables
from codex.training import train_model

from . import codex

_log = logging.getLogger("codex.run")


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

    if config != "default":
        config = Path(config)
    mod = model_module(model)
    reco = load_model(model, config)
    reco = Recommender.adapt(reco)

    if test_file:
        if assign_file or ratings_db or test_part:
            _log.error("--train/--test not compatible with alloc options")
            sys.exit(2)
        test_sets = fixed_test_sets(test_file, train_files)
    elif assign_file:
        if ratings_db is None:
            _log.error("must specify --ratings with --alloc")
            sys.exit(2)

        if not test_part:
            _log.error("must specify --test-part with --alloc")
            sys.exit(2)

        if test_file or train_files:
            _log.error("--train and --test incompatible with --alloc")
            sys.exit(2)

        test_sets = crossfold_test_sets(assign_file, ratings_db, test_part)

    predict = "predictions" in mod.outputs

    with duckdb.connect(fspath(output)) as db, connect_cluster() as cluster:
        create_result_tables(db, predictions=predict)

        for part, data in test_sets:
            _log.info("training model %s", reco)
            trained, metrics = train_model(reco, data)
            _log.info(
                "finished in %.0fs (%.0fs CPU, %s max RSS)",
                metrics.wall_time,
                metrics.cpu_time,
                naturalsize(metrics.rss_max_kb * 1024),
            )
            db.table("train_stats").insert([part] + list(metrics.dict().values()))

            _log.info("loading test data")
            with data.open_db() as test_db:
                test = data.test_ratings(test_db).to_df()
                if len(test) == 0:
                    _log.error("no test data found")

            n = 0
            db.execute("BEGIN")

            for result in run_recommender(trained, test, list_length, predict, cluster=cluster):
                n += 1
                if n % 1000 == 0:
                    db.execute("COMMIT")
                    db.execute("BEGIN")

                ntest = len(result.test)
                nrecs = len(result.recommendations)
                db.execute(
                    """
                    INSERT INTO user_metrics (run, user, wall_time, nrecs, ntruth)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [part, result.user, result.wall_time, nrecs, ntest],
                )
                # direct interpolation into sql is ok here, we know they are
                # integers (and this is not a security-conscious application).
                rec_df = result.recommendations
                db.from_df(rec_df).select(
                    duckdb.ConstantExpression(part),
                    duckdb.ConstantExpression(result.user),
                    "item",
                    "rank",
                    "score" if "score" in rec_df.columns else duckdb.ConstantExpression(None),
                ).insert_into("recommendations")
                if result.predictions is not None:
                    db.from_df(result.predictions).select(
                        duckdb.ConstantExpression(part),
                        duckdb.ConstantExpression(result.user),
                        "item",
                        "prediction",
                        "rating",
                    ).insert_into("predictions")

            db.execute("COMMIT")
            trained.close()


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
    with connect(fspath(assign)) as db:
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
