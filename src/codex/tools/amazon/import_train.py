from pathlib import Path

import click
import pyarrow as pa
import pyarrow.csv
from lenskit import DatasetBuilder
from lenskit.logging import get_logger

from . import amazon

_log = get_logger(__name__)


@amazon.command("import-train")
@click.option(
    "--output", "-o", type=Path, metavar="DIR", required=True, help="Output dataset location."
)
@click.argument("FILE", type=Path)
def import_train(output: Path, file: Path):
    "Convert a pre-split training data file."

    log = _log.bind(src=str(file))
    log.info("reading Amazon ratings")
    ratings = pyarrow.csv.read_csv(
        file,
        convert_options=pyarrow.csv.ConvertOptions(
            include_columns=["user_id", "parent_asin", "rating", "timestamp"],
            column_types={"rating": pa.float32()},
        ),
    )
    ratings = ratings.rename_columns({"parent_asin": "item_id"})

    log.info("creating dataset")
    dsb = DatasetBuilder()
    dsb.add_interactions(
        "rating",
        ratings,
        entities=["user", "item"],
        missing="insert",
        allow_repeats=False,
        default=True,
    )

    log.info("saving dataset", dst=str(output))
    dsb.save(output)
