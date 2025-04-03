from typing import Any

import numpy as np
import ray.tune


class RelativePlateauStopper(ray.tune.Stopper):
    metric: str
    mode: str
    min_improvement: float
    check_iters: int
    grace_period: int

    results: dict[str, list[float]]

    def __init__(
        self,
        metric: str,
        mode: str,
        min_improvement: float = 0.01,
        check_iters: int = 3,
        grace_period: int = 5,
    ):
        self.metric = metric
        self.mode = self.mode
        self.min_improvement = min_improvement
        self.check_iters = check_iters
        self.grace_period = grace_period

    def __call__(self, trial_id: str, result: dict[str, Any]) -> bool:
        mr = result[self.metric]
        if self.mode == "min":
            mr *= -1

        hist = self.results.get(trial_id, [])
        if len(hist) >= result["training_iteration"]:
            hist = hist[: result["training_iteration"] - 1]
        hist.append(mr)
        if len(hist) < self.grace_period:
            return False

        imp = np.diff(hist)[1:] / hist[:-1]
        # if we haven't improved more than min_imporvement lately, stop
        return np.all(imp[-self.check_iters :] < self.min_improvement).item()

    def stop_all(self) -> bool:
        return False
