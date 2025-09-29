import ray.tune as rt
from lenskit.als import ImplicitMFConfig, ImplicitMFScorer

PREDICTOR = False
SCORER = ImplicitMFScorer
DEFAULT_CONFIG = ImplicitMFConfig(user_embeddings="prefer")
STATIC_CONFIG = {"user_embeddings": "prefer"}

SEARCH_SPACE = {
    "embedding_size_exp": rt.randint(3, 10),
    "regularization": {
        "user": rt.loguniform(1e-5, 1),
        "item": rt.loguniform(1e-5, 1),
    },
    "weight": rt.uniform(5, 100),
}

OPTIONS = {"max_epochs": 30}
