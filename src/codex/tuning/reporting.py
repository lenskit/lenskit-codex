import ray.tune
import ray.tune.result
from lenskit.logging import get_logger, item_progress

_log = get_logger("codex.tuning")


class StatusCallback(ray.tune.Callback):
    def __init__(self, model: str, ds: str | None):
        self.log = _log.bind(model=model, dataset=ds)

    def on_trial_result(self, iteration, trials, trial, result, **info):
        metrics = {n: v for (n, v) in result.items() if n in ["RBP", "NDCG", "RecipRank", "RMSE"]}
        self.log.info("new trial result", iter=iteration, id=trial.trial_id, **metrics)


class ProgressReport(ray.tune.ProgressReporter):
    metric = None
    mode = None
    best_metric = None

    def __init__(self):
        super().__init__()
        self.done = set()

    def setup(self, start_time=None, total_samples=None, metric=None, mode=None, **kwargs):
        super().setup(start_time, total_samples, metric, mode, **kwargs)

        _log.info("setting up tuning status", total_samples=total_samples, metric=metric, mode=mode)
        extra = {metric: ".3f"} if metric is not None else {}
        self._bar = item_progress("Tuning trials", total_samples, extra)
        self.metric = metric
        self.mode = mode

    def report(self, trials, done, *sys_info):
        _log.debug("reporting trial completion", trial_count=len(trials))

        if done:
            _log.debug("search complete", trial_count=len(trials))
            self._bar.finish()
        else:
            total = len(trials)
            if total < self._bar.total:
                total = None

            n_new = 0
            for trial in trials:
                if trial.status == "TERMINATED" and trial.trial_id not in self.done:
                    self.done.add(trial.trial_id)
                    n_new += 1
                    _log.debug("finished trial", id=trial.trial_id, config=trial.config)
                    self._update_metric(trial)

            extra = {}
            if self.best_metric is not None:
                extra = {self.metric: self.best_metric}
            self._bar.update(n_new, total=total, **extra)

    def should_report(self, trials, done=False):
        if done:
            return True

        updated = any(self._update_metric(t) for t in trials)
        finished = set(t.trial_id for t in trials if t.status == "TERMINATED")
        if updated or finished - self.done:
            return True
        else:
            return False

    def _update_metric(self, trial):
        if self.metric is not None and trial.last_result and self.metric in trial.last_result:
            mv = trial.last_result[self.metric]
            if self.best_metric is None:
                self.best_metric = mv
                return True
            elif self.mode == "max" and mv > self.best_metric:
                self.best_metric = mv
                return True
            elif self.mode == "min" and mv < self.best_metric:
                self.best_metric = mv
                return True

        return False
