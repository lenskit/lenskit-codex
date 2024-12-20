import logging

from lenskit.pipeline import Component, Pipeline

from codex.data import TrainTestData
from codex.pipeline import base_pipeline
from codex.runlog import CodexTask

_log = logging.getLogger(__name__)


def train_and_wrap_model(
    name: str,
    model: Component,
    data: TrainTestData,
    pipe: Pipeline | None = None,
    predicts_ratings: bool = False,
) -> tuple[Pipeline, CodexTask]:
    "Train a recommendation model on input data."
    with data.open_db() as db:
        train = data.train_data(db)

    if pipe is None:
        _log.info("creating recommendation pipeline %s", name)
        pipe = base_pipeline(name, model, predicts_ratings)
    else:
        _log.debug("reusing recommendation pipeline")
        pipe.replace_component(
            "scorer", model, query=pipe.node("query"), items=pipe.node("candidate-selector")
        )

    with CodexTask(
        label=f"generate-{model}/train",
        tags=["train"],
        reset_hwm=True,
    ) as task:
        pipe.train(train, retrain=False)

    return pipe, task
