import json
from pathlib import Path

import click
import structlog
from lenskit import Pipeline

from codex.inference import recommend_and_save
from codex.layout import model_dir
from codex.outputs import RunOutput
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.splitting import SplitSet, load_split_set
from codex.training import train_task

from . import codex

_log = structlog.stdlib.get_logger(__name__)


@codex.command("generate")
@click.option(
    "--pipeline-file",
    "pipeline_file",
    metavar="FILE",
    type=Path,
    help="Load pipeline from FILE.",
)
@click.option(
    "-n",
    "--list-length",
    type=int,
    metavar="N",
    help="control recommendation list length",
    default=100,
)
@click.option("-o", "--output", "out_dir", type=Path, metavar="N", help="Specify output directory.")
@click.option("--ds-name", help="Name of the dataset.")
@click.option(
    "--split", "split", type=Path, required=True, help="Path to the split spec or directory."
)
@click.option(
    "-p",
    "--test-part",
    metavar="PARTS",
    help="Test on specified part(s), comma-separated; -part to negate.",
)
@click.argument("MODEL")
def generate(
    model: str | None,
    pipeline_file: Path | None,
    out_dir: Path,
    split: Path,
    test_part: str | None,
    ds_name: str | None = None,
    list_length: int = 100,
):
    """
    Generate recommendations using a default or configured algorithm.
    """

    if pipeline_file is None:
        if model is None:
            _log.error("no pipeline or model specified")
            raise click.UsageError("must specify --pipeline-file or model name")
        pipeline_file = model_dir(model) / "pipeline.json"

    pipeline = Pipeline.load_config(pipeline_file)
    if model is not None and pipeline.name != model:
        _log.warn("pipeline name %s does not match model name %s", pipeline.name, model)
    if model is None:
        model = pipeline.name

    output = RunOutput(out_dir)
    output.initialize()

    data_info = DataModel(dataset=ds_name, split=split.stem)
    with (
        CodexTask(
            label=f"generate {model}",
            tags=["generate"],
            scorer=ScorerModel(name=model),
            data=data_info,
        ) as root_task,
        output.user_metric_collector() as metric_out,
    ):
        split_set = load_split_set(split)
        parts = select_parts(split_set, test_part)

        log = _log.bind(task_id=str(root_task.task_id))
        for part in parts:
            data_info.part = part
            plog = log.bind(part=part)
            plog.info("loading data")
            data = split_set.get_part(part)
            pipe, task = train_task(pipeline, data.train, data_info)
            output.record_log("training", task)

            shard = f"part={part}"
            with CodexTask(
                label=f"recommend {model}",
                tags=["recommend"],
                reset_hwm=True,
                scorer=ScorerModel(name=model, config=pipe.config.components["scorer"].config),
                data=data_info,
            ) as task:
                rec_out = output.recommendations_hive_path / shard / "data.parquet"
                if pipe.node("rating-predictor", missing=None) is not None:
                    pred_out = output.predictions_hive_path / shard / "data.parquet"
                else:
                    pred_out = None

                recommend_and_save(
                    pipe,
                    data.test,
                    list_length,
                    rec_out,
                    pred_out,
                    metric_out,
                    meta={"part": part},
                )

            output.record_log("inference", task)

        log.info("finished all parts")
        output.repack_output_lists()


def select_parts(split: SplitSet, part: str | None) -> list[str]:
    if part is None:
        return split.parts
    elif part.startswith("-"):
        exp = part[1:]
        return [p for p in split.parts if p != exp]
    else:
        return part.split(",")


def load_config(path: Path | None):
    if path is None:
        return {}
    else:
        with path.open("rt") as jsf:
            obj = json.load(jsf)
        if "config" in obj:
            obj = obj["config"]
        return obj
