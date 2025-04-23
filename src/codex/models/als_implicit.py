import ray.tune as rt
from lenskit.als import ImplicitMFConfig, ImplicitMFScorer

PREDICTOR = False
SCORER = ImplicitMFScorer
DEFAULT_CONFIG = ImplicitMFConfig(user_embeddings="prefer")
STATIC_CONFIG = {"user_embeddings": "prefer"}

SEARCH_SPACE = {
    "embedding_size": rt.lograndint(4, 512, base=2),
    "regularization": {
        "user": rt.loguniform(1e-5, 1),
        "item": rt.loguniform(1e-5, 1),
    },
    "damping": {
        "user": rt.loguniform(1e-12, 100),
        "item": rt.loguniform(1e-12, 100),
    },
    "weight": rt.uniform(5, 100),
}

OPTIONS = {"max_epochs": 30}
