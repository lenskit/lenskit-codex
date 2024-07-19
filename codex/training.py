import logging
import pickle
import resource
import sys
import time
from dataclasses import dataclass
from multiprocessing.managers import SharedMemoryManager
from pathlib import Path
from subprocess import PIPE, Popen
from typing import TypedDict

import manylog
from lenskit.algorithms import Algorithm
from lenskit.parallel.serialize import shm_deserialize, shm_serialize
from sandal.project import project_root

from codex.data import TrainTestData

_log = logging.getLogger(__name__)

TM_SCHEMA = """
CREATE TABLE train_metrics (
    run_idx BIGINT PRIMARY KEY,
    wall_time FLOAT,
    cpu_time FLOAT,
    cpu_usr FLOAT,
    cpu_sys FLOAT,
    max_rss_mem FLOAT,
    max_cuda_mem FLOAT,
)
"""


class TrainingMetrics(TypedDict):
    wall_time: float
    cpu_time: float
    cpu_usr: float
    cpu_sys: float
    max_rss_mem: float
    max_cuda_mem: float


def train_model(
    model: Algorithm, data: TrainTestData, mgr: SharedMemoryManager
) -> tuple[Algorithm, TrainingMetrics]:
    "Train a recommendaiton model on input data."
    manylog.initialize()
    input = shm_serialize((model, data), mgr)

    _log.info("spawning training process")
    proc = Popen(
        [sys.executable, "-m", "codex.training"],
        env={"PYTHONPATH": project_root()},
        stdout=PIPE,
        stdin=PIPE,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    pickle.dump(input, proc.stdin, pickle.HIGHEST_PROTOCOL)
    proc.stdin.close()


def _train_worker():
    manylog.initialize()
    _log.debug("reading model from stdin")
    model: Algorithm
    data: TrainTestData
    model, data = pickle.load(sys.stdin.buffer)

    _log.info("preparing to train model %s", model)

    start = time.perf_counter()
