import implicit.gpu
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

TUNE_CPUS = 4
# we can train BPR on CPU, it's just slower
if implicit.gpu.HAS_CUDA:
    TUNE_GPUS = 0.25
