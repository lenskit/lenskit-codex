import json
import logging
import re
import sys
from os import fspath
from pathlib import Path
from typing import Iterator

import click
import pandas as pd
from duckdb import connect
from humanize import naturalsize
from lenskit import batch
from lenskit.algorithms import Algorithm, Recommender

from codex.data import TrainTestData, fixed_tt_data, partition_tt_data
from codex.models import load_model
from codex.training import train_model

from . import codex

_log = logging.getLogger("codex.run")


@codex.command("generate")
@click.option("--default", "config", help="use default configuration", flag_value="default")
@click.option("--param-file", "config", metavar="FILE", help="configure model from FILE")
@click.option(
    "-n", "--list-length", type=int, metavar="N", help="control recommendation list length"
)
@click.option("--recommendations", "recs_file", type=Path, help="recommendation output file")
@click.option("--predictions", "preds_file", type=Path, help="prediction output file")
@click.option("--stats", "stats_file", type=Path, help="statistics output file")
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
    train_files: list[Path],
    list_length: int = 100,
    recs_file: Path | None = None,
    preds_file: Path | None = None,
    assign_file: Path | None = None,
    stats_file: Path | None = None,
    ratings_db: Path | None = None,
    test_file: Path | None = None,
    test_part: str | None = None,
):
    """
    Generate recommendations using a default or configured algorithm.
    """

    if config != "default":
        config = Path(config)
    reco = load_model(model, config)
    reco = Recommender.adapt(reco)

    recs = [] if recs_file else None
    preds = [] if preds_file else None
    if stats_file:
        stats_file.parent.mkdir(exist_ok=True, parents=True)
        stats = stats_file.open("w")
    else:
        stats = None

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

    for data in test_sets:
        _log.info("training model %s", reco)
        reco, metrics = train_model(reco, data)
        _log.info(
            "finished in %.0fs (%.0fs CPU, %s max RSS)",
            metrics.wall_time,
            metrics.cpu_time,
            naturalsize(metrics.rss_max_kb * 1024),
        )

        with data.open_db() as db:
            test = data.test_ratings(db).to_df()
            if len(test) == 0:
                _log.error("no test data found")

        if recs is not None:
            recs.append(recommend(reco, test, list_length))
        if preds is not None:
            preds.append(predict(reco, test))

        if stats is not None:
            summary = {"n_users": test["user"].nunique()}
            summary.update(metrics.dict())
            print(json.dumps(summary), file=stats)

    if recs is not None:
        recs = pd.concat(recs, ignore_index=True)
        _log.info("saving %d recommendations to %s", len(recs), recs_file)
        recs.to_parquet(recs_file, compression="zstd")

    if preds is not None:
        preds = pd.concat(preds, ignore_index=True)
        _log.info("saving %d predictions to %s", len(preds), preds_file)
        preds.to_parquet(preds_file, compression="zstd")

    if stats is not None:
        stats.close()


def fixed_test_sets(test: Path, train: list[Path]) -> Iterator[TrainTestData]:
    # now figure out how to load things
    if test.suffix == ".parquet":
        # we should have training data, and no parts
        _log.info("using fixed test set %s", test)
        if not train:
            _log.error("must specify training data with test data")
        yield fixed_tt_data(test, train)
    else:
        raise ValueError(f"unsupported test file {test}")


def crossfold_test_sets(assign: Path, ratings: Path, parts: str):
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
        yield partition_tt_data(assign, ratings, part)


def recommend(reco: Algorithm, test: pd.DataFrame, N: int):
    _log.info("generating recommendations")
    test_users = test["user"].unique()
    n_jobs = 1 if len(test_users) < 1000 else None
    recs = batch.recommend(reco, test_users, N, n_jobs=n_jobs)
    return recs


def predict(reco: Algorithm, test: pd.DataFrame):
    _log.info("predicting test ratings")
    n_jobs = 1 if test["user"].nunique() < 1000 else None
    preds = batch.predict(reco, test, n_jobs=n_jobs)
    return preds
