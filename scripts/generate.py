#!/usr/bin/env python3
"""
Generate recommendations from a recommender.

Usage:
    run.py [-v] (--default | --param-file=FILE) [-n N]
        [--train-part=PART] [--test-part=PART]
        [--recommendations=FILE] [--predictions=FILE] [--stats=FILE]
        [--ratings=DB] MODEL DB

Options:
    -v, --verbose
        enable verbose logging
    -n N, --list-length=N
        generate recommendation lists of length N [default: 100]
    --train-part=PART
        train on partition(s) PART instead of all non-test partitions
    --test-part=PART
        evaluate on partition(s) PART [default: test]
    --recommendations=FILE
        write recommendations to FILE
    --predictions=FILE
        write predictions to FILE
    --stats=FILE
        write run statistics to FILE
    --ratings=DB
        load ratings from DB to go with test partitions in main DB
    MODEL
        name of the model to run
    DB
        path to the test database
    OUT
        path to the output database
"""

import json
import logging
import sys
from inspect import Parameter, signature
from pathlib import Path
from typing import Iterator

import pandas as pd
from docopt import ParsedOptions, docopt
from humanize import naturalsize
from lenskit import batch
from lenskit.algorithms import Algorithm, Recommender
from sandal import autoroot  # noqa: F401
from sandal.cli import setup_logging
from sandal.project import here
from seedbank import init_file

from codex.data import TrainTestData, fixed_tt_data, parse_parts, partition_tt_data
from codex.models import model_module
from codex.training import train_model

_log = logging.getLogger("codex.run")


def main():
    assert __doc__
    opts = docopt(__doc__)
    setup_logging(opts["--verbose"])

    init_file(here("config.toml"))

    mod = model_module(opts["MODEL"])
    if opts["--default"]:
        reco = mod.default()
        reco = Recommender.adapt(reco)
    elif opts["--param-file"]:
        pf = Path(opts["--param-file"])
        params = json.loads(pf.read_text())
        fc_sig = signature(mod.from_config)
        has_kw = any(p.kind == Parameter.VAR_KEYWORD for p in fc_sig.parameters.values())
        if not has_kw:
            params = {p: v for (p, v) in params.items() if p in fc_sig.parameters.keys()}
        reco = mod.from_config(**params)
        reco = Recommender.adapt(reco)
    else:
        _log.error("no valid model mode specified")
        sys.exit(1)

    recs = [] if opts["--recommendations"] else None
    preds = [] if opts["--predictions"] else None
    if opts["--stats"]:
        sp = Path(opts["--stats"])
        sp.parent.mkdir(exist_ok=True, parents=True)
        stats = open(opts["--stats"], "w")
    else:
        stats = None

    for data in test_sets(opts):
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
            recs.append(recommend(opts, reco, test))
        if preds is not None:
            preds.append(predict(opts, reco, test))

        if stats is not None:
            summary = {"n_users": test["user"].nunique()}
            summary.update(metrics.dict())
            print(json.dumps(summary), file=stats)

    if recs is not None:
        recs = pd.concat(recs, ignore_index=True)
        rec_f = opts["--recommendations"]
        _log.info("saving %d recommendations to %s", len(recs), rec_f)
        recs.to_parquet(rec_f, compression="zstd")

    if preds is not None:
        preds = pd.concat(preds, ignore_index=True)
        pred_f = opts["--predictions"]
        _log.info("saving %d predictions to %s", len(preds), pred_f)
        preds.to_parquet(pred_f, compression="zstd")


def test_sets(opts: ParsedOptions) -> Iterator[TrainTestData]:
    test_parts = parse_parts(opts["--test-part"])
    train_parts = parse_parts(opts["--train-part"]) if opts["--train-part"] else None

    _log.info("runing on %d test parts", len(test_parts))
    for part in test_parts:
        if opts["--ratings"]:
            if train_parts is None:
                _log.info("using crossfold partition %s", part)
                yield partition_tt_data(opts["DB"], opts["--ratings"], int(part))
            else:
                _log.error("unsupported configuration")
                raise RuntimeError("unsupported configuration")
        else:
            _log.info("using fixed test set %s", part)
            yield fixed_tt_data(opts["DB"], str(part), train=train_parts)


def recommend(opts: ParsedOptions, reco: Algorithm, test: pd.DataFrame):
    _log.info("generating recommendations")
    N = int(opts["--list-length"])
    test_users = test["user"].unique()
    n_jobs = 1 if len(test_users) < 1000 else None
    recs = batch.recommend(reco, test_users, N, n_jobs=n_jobs)
    return recs


def predict(opts: ParsedOptions, reco: Algorithm, test: pd.DataFrame):
    _log.info("predicting test ratings")
    n_jobs = 1 if test["user"].nunique() < 1000 else None
    preds = batch.predict(reco, test, n_jobs=n_jobs)
    return preds


if __name__ == "__main__":
    main()
