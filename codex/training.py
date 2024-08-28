import logging
from typing import NamedTuple

from lenskit.algorithms import Algorithm
from lenskit.sharing import PersistedModel, persist
from lenskit.util.parallel import run_sp

from codex.data import TrainTestData
from codex.resources import ResourceMetrics, resource_monitor

_log = logging.getLogger(__name__)


class TrainResult(NamedTuple):
    model: PersistedModel
    metrics: ResourceMetrics


def train_model(model: Algorithm, data: TrainTestData) -> TrainResult:
    "Train a recommendation model on input data."

    _log.info("spawning training process")
    return run_sp(_train_worker, model, data)


def _train_worker(model: Algorithm, data: TrainTestData) -> TrainResult:
    _log.info("loading training data")
    with data.open_db() as db:
        train = data.train_ratings(db).to_df()

    _log.info("preparing to train model %s", model)
    with resource_monitor() as mon:
        model.fit(train)

    stored = persist(model)

    return TrainResult(stored.transfer(), mon.metrics())
