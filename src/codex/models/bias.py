import ray.tune as rt
from lenskit.basic.bias import BiasConfig, BiasScorer

PREDICTOR = True
SCORER = BiasScorer
DEFAULT_CONFIG = BiasConfig(damping=50)

SEARCH_SPACE = {
    "damping": {
        "user": rt.loguniform(1e-1, 100),
        "item": rt.loguniform(1e-1, 100),
    }
}

# bias is single-threaded
TUNE_CPUS = 1
