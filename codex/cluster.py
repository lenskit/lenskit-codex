import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

import ipyparallel as ipp

_log = logging.getLogger(__name__)


@contextmanager
def connect_cluster(cluster: ipp.Cluster | ipp.Client | None = None) -> Generator[ipp.Client]:
    count = os.environ.get("LK_NUM_PROCS", None)
    config = os.environ.get("LK_IPP_CLUSTER", None)

    if isinstance(cluster, ipp.Client):
        yield cluster
        return
    elif cluster is None and config is not None:
        _log.info("connecting to cluster profile %s", config)
        with ipp.Client(profile=config) as client:
            yield client
        return

    if count is not None:
        count = int(count)
    else:
        count = min(os.cpu_count(), 8)  # type: ignore

    if cluster is None:
        _log.info("starting cluster with %s workers", count)
        with ipp.Cluster(n=count) as client:
            yield client
    else:
        with cluster.connect_client_sync() as client:
            yield client
