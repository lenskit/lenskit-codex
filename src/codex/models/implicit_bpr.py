import ray.tune as rt
from lenskit.implicit import BPR

SCORER = BPR
DEFAULT_CONFIG = {"factors": 50}

SEARCH_SPACE = {
    "factors": rt.lograndint(4, 512, base=2),
    "learning_rate": rt.loguniform(1e-5, 1e-1),
    "regularization": rt.loguniform(1e-5, 1),
    "iterations": rt.randint(50, 200),
}

TUNE_CPUS = "4"
