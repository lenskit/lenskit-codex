import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Callable

import ray
import ray.actor
import structlog
import torch
from lenskit.logging import Task
from lenskit.logging.worker import WorkerContext, WorkerLogConfig
from lenskit.parallel.config import (
    ParallelConfig,
    ensure_parallel_init,
    get_parallel_config,
    initialize,
)
from lenskit.parallel.ray import init_cluster

_log = structlog.stdlib.get_logger(__name__)


def ensure_cluster_init():
    if not ray.is_initialized():
        try:
            ray.init(address="auto")
        except ConnectionError:
            init_cluster(global_logging=True, worker_parallel=get_parallel_config())


class CodexActor:
    """
    Base class for Codex actors, with resource management.
    """

    context: WorkerContext
    task: Task

    def __init__(self, parallel: ParallelConfig, logging: WorkerLogConfig):
        pid = os.getpid()
        self.context = WorkerContext(logging)
        self.context.start()
        initialize(parallel)
        self.task = Task(f"codex worker {pid} {self}", reset_hwm=True, subprocess=True)
        self.task.start()

    def finish(self) -> Task:
        self.task.finish()
        self.context.shutdown()
        return self.task

    def __str__(self):
        return self.__class__.__name__


@contextmanager
def worker_pool[T, **P](
    actor: Callable[P, T], *args: P.args, **kwargs: P.kwargs
) -> Generator[ray.util.ActorPool, None, None]:
    log = _log.bind()
    ensure_parallel_init()
    cfg = get_parallel_config()
    n_jobs = cfg.processes

    log = log.bind(n_jobs=n_jobs)
    log.info("creating actor pool")
    actor = ray.remote(actor)  # type: ignore
    workers = [actor.remote(*args, **kwargs) for i in range(n_jobs)]

    pool = ray.util.ActorPool(workers)
    try:
        yield pool
    finally:
        log.info("shutting down pool")
        current = Task.current()
        done = [w.finish.remote() for w in workers]
        for task in done:
            st = ray.get(task)
            if st is None:
                log.warn("task result %r has no task", task)
            elif current is not None:
                current.add_subtask(st)


def serialize_tensor(tensor: torch.Tensor):
    if tensor.is_sparse_csr:
        return "csr", (
            tensor.crow_indices().cpu().numpy(),
            tensor.col_indices().cpu().numpy(),
            tensor.values().cpu().numpy(),
            tensor.shape,
        )
    elif tensor.is_sparse:
        return "coo", (tensor.indices().cpu().numpy(), tensor.values().cpu().numpy(), tensor.shape)
    else:
        return "dense", tensor.cpu().numpy()


def deserialize_tensor(data):
    tag, array = data
    match tag:
        case "dense":
            return torch.from_numpy(array)
        case "csr":
            ri, ci, vs, shape = array
            return torch.sparse_csr_tensor(crow_indices=ri, col_indices=ci, values=vs, size=shape)
        case "coo":
            indices, vs, shape = array
            return torch.sparse_coo_tensor(indices=indices, values=vs, size=shape)
        case _:
            raise ValueError(f"invalid tensor type {tag}")


ray.util.register_serializer(
    torch.Tensor, serializer=serialize_tensor, deserializer=deserialize_tensor
)
