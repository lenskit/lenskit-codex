from pathlib import Path

import click
import structlog

from codex.cluster import ensure_cluster_init
from codex.inference import recommend_and_save
from codex.modelcfg import load_config
from codex.outputs import RunOutput
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.splitting import SplitSet, load_split_set
from codex.training import train_task

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
@click.option("-o", "--output", "out_dir", type=Path, metavar="N", help="specify output database")
@click.option("--ds-name", help="name of the dataset")
@click.option("--split", "split", type=Path, help="path to the split spec (or base file)")
@click.option(
    "-p",
    "--test-part",
    metavar="PARTS",
    help="test on specified part(s), comma-separated; -part to negate",
)
@click.argument("MODEL", required=True)
def generate(
    model: str,
    config: str | Path,
    out_dir: Path,
    split: Path,
    ds_name: str | None = None,
    test_part: str | None = None,
    list_length: int = 100,
):
    """
    Generate recommendations using a default or configured algorithm.
    """

    if config == "default":
        cfg_path = None
    else:
        cfg_path = Path(config)

    mod_cfg = load_config(model)

    ensure_cluster_init()

    output = RunOutput(out_dir)
    output.initialize()

    data_info = DataModel(dataset=ds_name, split=split.stem, part=test_part)
    with (
        CodexTask(
            label=f"generate {model}",
            tags=["generate"],
            scorer=ScorerModel(name=model),
            data=data_info,
        ) as root_task,
        load_split_set(split) as split_set,
        output.user_metric_collector() as metric_out,
    ):
        parts = select_parts(split_set, test_part)

        log = _log.bind(task_id=str(root_task.task_id))
        for part in parts:
            plog = log.bind(part=part)
            plog.info("loading data")
            data = split_set.get_part(part)
            instance = mod_cfg.instantiate(cfg_path)
            pipe, task = train_task(instance, data.train, data_info)
            output.record_log("training", task)

            shard = f"part={part}"
            with CodexTask(
                label=f"recommend {model}",
                tags=["recommend"],
                reset_hwm=True,
                scorer=ScorerModel(name=model, config=instance.params),
                data=data_info,
            ) as task:
                recommend_and_save(
                    pipe,
                    data.test,
                    list_length,
                    output.recommendations_hive_path / shard,
                    output.predictions_hive_path / shard if mod_cfg.predictor else None,
                    metric_out,
                    meta={"part": part},
                )

            output.record_log("inference", task)

        log.info("finished all parts")


def select_parts(split: SplitSet, part: str | None) -> list[str]:
    if part is None:
        return split.parts
    elif part.startswith("-"):
        exp = part[1:]
        return [p for p in split.parts if p != exp]
    else:
        return part.split(",")
