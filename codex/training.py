import logging
from typing import NamedTuple

from lenskit.algorithms import Algorithm
from lenskit.sharing import PersistedModel, persist
from lenskit.util.parallel import run_sp
from sandal.project import project_root
from xshaper import Monitor, Run, configure
from xshaper.model import RunRecord

from codex.data import TrainTestData

_log = logging.getLogger(__name__)


class TrainResult(NamedTuple):
    model: PersistedModel
    record: RunRecord


def train_model(model: Algorithm, data: TrainTestData) -> TrainResult:
    "Train a recommendation model on input data."

    _log.info("spawning training process")
    return run_sp(_train_worker, model, data)


def _train_worker(model: Algorithm, data: TrainTestData) -> TrainResult:
    _log.info("loading training data")
    # FIXME: sprinkling this everywhere is suboptimal
    configure(project_root() / "run-log")
    with Monitor(), Run(tags=["lenskit", "train", "worker"], concurrent=True):
        with data.open_db() as db:
            train = data.train_ratings(db).to_df()

        _log.info("preparing to train model %s", model)
        with Run(tags=["lenskit", "train", "worker", "fit"]) as run:
            model.fit(train)

        stored = persist(model)

    return TrainResult(stored.transfer(), run.record)
