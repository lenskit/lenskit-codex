import ray.tune as rt
from lenskit.als import BiasedMFConfig, BiasedMFScorer

PREDICTOR = True
SCORER = BiasedMFScorer
DEFAULT_CONFIG = BiasedMFConfig(user_embeddings="prefer")
STATIC_CONFIG = {"user_embeddings": "prefer"}

SEARCH_SPACE = {
    "embedding_size_exp": rt.randint(3, 10),
    "regularization": {
        "user": rt.loguniform(1e-5, 1),
        "item": rt.loguniform(1e-5, 1),
    },
    "damping": {
        "user": rt.loguniform(1e-12, 100),
        "item": rt.loguniform(1e-12, 100),
    },
}

OPTIONS = {"max_epochs": 30}
