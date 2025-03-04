import structlog
from humanize import metric, naturalsize
from lenskit.data import Dataset
from lenskit.pipeline import Component, Pipeline

from codex.modelcfg import ModelInstance
from codex.pipeline import base_pipeline
from codex.runlog import CodexTask, DataModel, ScorerModel

_log = structlog.stdlib.get_logger(__name__)


def train_task(
    model: ModelInstance, data: Dataset, data_info: DataModel
) -> tuple[Pipeline, CodexTask]:
    log = _log.bind(name=model.name, config=model.params)
    log.info("training model")
    with CodexTask(
        label=f"train {model.name}",
        tags=["train"],
        reset_hwm=True,
        scorer=ScorerModel(name=model.name, config=model.params),
        data=data_info,
    ) as task:
        try:
            pipe = train_and_wrap_model(
                model.scorer,
                data,
                predicts_ratings=model.config.predictor,
                name=model.name,
            )
        except Exception as e:
            log.error("model training failed", exc_info=e)
            raise e

    log.debug("run record: %s", task.model_dump_json(indent=2))
    log.info(
        "finished in %.0fs (%.0fs CPU, %s, %s peak RSS)",
        task.duration,
        task.cpu_time,
        metric(task.chassis_power / 3600, "Wh")
        if task.chassis_power is not None
        else "power unknown",
        naturalsize(task.peak_memory) if task.peak_memory else "unknown",
    )
    return pipe, task


def train_and_wrap_model(
    model: Component,
    data: Dataset,
    pipe: Pipeline | None = None,
    predicts_ratings: bool = False,
    *,
    name: str = "unnamed",
) -> Pipeline:
    "Train a recommendation model on input data."

    if pipe is None:
        _log.info("creating recommendation pipeline %s", name)
        pipe = base_pipeline(name, model, predicts_ratings)
    else:
        _log.debug("reusing recommendation pipeline")
        pipe.replace_component(
            "scorer", model, query=pipe.node("query"), items=pipe.node("candidate-selector")
        )

    pipe.train(data, retrain=False)

    return pipe
