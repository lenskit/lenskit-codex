from __future__ import annotations

import logging
import os.path
import zipfile
from abc import ABC, abstractmethod
from os import fspath
from pathlib import Path

import click
import duckdb
import numpy as np
import pandas as pd

from . import movielens

_log = logging.getLogger(__name__)


@movielens.command("import")
@click.option("--stat-sql", type=Path, help="statistics SQL script")
@click.argument("ZIPFILE", type=Path)
def import_ml(zipfile: Path, stat_sql: Path | None = None):
    _log.info("importing %s", zipfile)

    data = open_data(zipfile)

    dbf = zipfile.with_name("ratings.duckdb")

    with data:
        dirname = data.get_dirname()
        with data.archive.open(os.path.join(dirname, data.rating_file)) as rf:
            rate_df = data.read_ratings(rf)
        _log.info("read %d ratings", len(rate_df))

        rate_df["timestamp"] = pd.to_datetime(rate_df["timestamp"], unit="s")

        _log.info("saving %s", dbf)
        with duckdb.connect(fspath(dbf)) as db:
            rel = db.from_df(rate_df)
            rel.create("ratings")
            if stat_sql:
                _log.info("computing stats with %s", stat_sql)
                sql = stat_sql.read_text()
                db.execute(sql)


class MLData(ABC):
    path: Path
    rating_file: str
    archive: zipfile.ZipFile

    def __init__(self, path: Path):
        self.path = path

    def get_dirname(self) -> str:
        infos = self.archive.infolist()
        first = infos[0]
        if not first.is_dir:
            raise RuntimeError("zipfile expected to begin with directory")
        return first.filename

    @abstractmethod
    def read_ratings(self, file) -> pd.DataFrame: ...

    def __enter__(self):
        self.archive = zipfile.ZipFile(self.path, "r")
        self.archive.__enter__()
        return self

    def __exit__(self, *args, **kwargs):
        self.archive.__exit__(*args, **kwargs)


def open_data(file: Path) -> MLData:
    name = file.stem
    if name == "ml-100k":
        return ML100K(file)
    elif name == "ml-1m" or name == "ml-10m":
        return MLM(file)
    else:
        return MLCurrent(file)


class ML100K(MLData):
    rating_file = "u.data"

    def read_ratings(self, file) -> pd.DataFrame:
        return pd.read_csv(
            file,
            sep="\t",
            header=None,
            names=["user_id", "item_id", "rating", "timestamp"],
            dtype={
                "user_id": np.int32,
                "item_id": np.int32,
                "rating": np.float32,
                "timestamp": np.int32,
            },
        )


class MLM(MLData):
    rating_file = "ratings.dat"

    def read_ratings(self, file) -> pd.DataFrame:
        return pd.read_csv(
            file,
            sep=":",
            header=None,
            names=["user_id", "_ui", "item_id", "_ir", "rating", "_rt", "timestamp"],
            usecols=[0, 2, 4, 6],
            dtype={
                "user_id": np.int32,
                "item_id": np.int32,
                "rating": np.float32,
                "timestamp": np.int32,
            },
        )[["user_id", "item_id", "rating", "timestamp"]]


class MLCurrent(MLData):
    rating_file = "ratings.csv"

    def read_ratings(self, file) -> pd.DataFrame:
        return pd.read_csv(
            file,
            dtype={
                "movieId": np.int32,
                "userId": np.int32,
                "rating": np.float64,
                "timestamp": np.int32,
            },
        ).rename(columns={"userId": "user_id", "movieId": "item_id"})
