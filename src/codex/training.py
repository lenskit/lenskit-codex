import structlog
from humanize import metric, naturalsize
from lenskit.data import Dataset
from lenskit.pipeline import Pipeline
from lenskit.random import RNGInput
from lenskit.training import TrainingOptions

from codex.models import ModelFactory
from codex.random import rng_seed
from codex.runlog import CodexTask, DataModel, ScorerModel

_log = structlog.stdlib.get_logger(__name__)


def train_task(
    pipeline: Pipeline,
    data: Dataset,
    data_info: DataModel,
    factory: ModelFactory | None = None,
    rng: RNGInput | None = None,
) -> tuple[Pipeline, CodexTask]:
    log = _log.bind(name=pipeline.name)
    if rng is None:
        rng = rng_seed("train", pipeline.name)
    log.info("training model")
    with CodexTask(
        label=f"train {pipeline.name}",
        tags=["train"],
        reset_hwm=True,
        scorer=ScorerModel(name=pipeline.name, config=pipeline.config.components["scorer"].config),
        data=data_info,
    ) as task:
        try:
            pipe = pipeline.clone()
            pipe.train(data, TrainingOptions(retrain=False, rng=rng))
        except Exception as e:
            log.error("model training failed", exc_info=e)
            raise e

    log.debug("run record: %s", task.model_dump_json(indent=2))
    log.info(
        "finished in %.0fs (%.0fs CPU, %s, %s peak RSS)",
        task.duration,
        task.cpu_time,
        metric(task.system_power / 3600, "Wh")
        if task.system_power is not None
        else "power unknown",
        naturalsize(task.peak_memory) if task.peak_memory else "unknown",
    )
    return pipe, task
