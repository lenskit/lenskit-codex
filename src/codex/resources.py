import resource
import time
from dataclasses import dataclass, fields
from typing import Self


@dataclass
class ResourceMetrics:
    wall_time: float
    cpu_time: float
    cpu_usr: float
    cpu_sys: float
    rss_max_kb: float
    # gpu_time: float | None = None
    # max_gpu_mem: float | None = None

    def dict(self):
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name, None) is not None
        }


class resource_monitor:
    start_time: float
    start_rusage: resource.struct_rusage
    end_time: float
    end_rusage: resource.struct_rusage

    def __enter__(self) -> Self:
        self.start_time = time.perf_counter()
        self.start_rusage = resource.getrusage(resource.RUSAGE_SELF)
        return self

    def __exit__(self, *_args, **_kwargs):
        self.end_time = time.perf_counter()
        self.end_rusage = resource.getrusage(resource.RUSAGE_SELF)

    def metrics(self) -> ResourceMetrics:
        stime = self.end_rusage.ru_stime - self.start_rusage.ru_stime
        utime = self.end_rusage.ru_utime - self.start_rusage.ru_utime
        return ResourceMetrics(
            wall_time=self.end_time - self.start_time,
            cpu_time=stime + utime,
            cpu_sys=stime,
            cpu_usr=utime,
            rss_max_kb=self.end_rusage.ru_maxrss,
        )
