from pathlib import Path

import click
import structlog
from humanize import naturalsize

from codex.cluster import ensure_cluster_init
from codex.collect import NDJSONCollector
from codex.inference import recommend_and_save
from codex.modelcfg import load_config
from codex.runlog import CodexTask, DataModel, ScorerModel
from codex.splitting import SplitSet, load_split_set
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
    output: Path,
    split: Path,
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

    output.mkdir(exist_ok=True, parents=True)
    (output / "training.json").unlink(missing_ok=True)
    (output / "inference.json").unlink(missing_ok=True)

    with (
        load_split_set(split) as split_set,
        CodexTask(
            label=f"generate {model}", tags=["generate"], scorer=ScorerModel(name=model)
        ) as root_task,
        NDJSONCollector(output / "user-metrics.ndjson.zst") as metric_out,
    ):
        parts = select_parts(split_set, test_part)

        log = _log.bind(task_id=str(root_task.task_id))
        for part in parts:
            plog = log.bind(part=part)
            plog.info("loading data")
            data = split_set.get_part(part)
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
                    instance.scorer, data.train, predicts_ratings=mod_cfg.predictor, name=model
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
                    data.test,
                    list_length,
                    output / "recommendations" / shard,
                    output / "predictions" / shard if mod_cfg.predictor else None,
                    metric_out,
                    meta={"part": part},
                )

            with open(output / "inference.json", "a") as jsf:
                print(task.model_dump_json(), file=jsf)

        log.info("finished all parts")


def select_parts(split: SplitSet, part: str | None) -> list[str]:
    if part is None:
        return split.parts
    elif part.startswith("-"):
        exp = part[1:]
        return [p for p in split.parts if p != exp]
    else:
        return part.split(",")
