import ray.tune as rt
from lenskit.basic.bias import BiasConfig, BiasScorer
from lenskit.data import Dataset

PREDICTOR = True
SCORER = BiasScorer
DEFAULT_CONFIG = BiasConfig(damping=50)

SEARCH_SPACE = {
    "damping": {
        "user": rt.loguniform(1e-1, 100),
        "item": rt.loguniform(1e-1, 100),
    }
}


def tune_resources(ds: Dataset):
    # rough approximation
    return {
        "CPU": 1,
        "memory": ds.interaction_count * 400,
    }
