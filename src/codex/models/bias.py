import ray.tune as rt
from lenskit.basic.bias import BiasConfig, BiasScorer

PREDICTOR = True
SCORER = BiasScorer
DEFAULT_CONFIG = BiasConfig(damping=50)

SEARCH_SPACE = {
    "damping.user": rt.loguniform(1e-12, 100),
    "damping.item": rt.loguniform(1e-12, 100),
}
