import ray.tune as rt
from lenskit.knn import UserKNNConfig, UserKNNScorer

PREDICTOR = True
SCORER = UserKNNScorer
DEFAULT_CONFIG = UserKNNConfig(max_nbrs=20, min_nbrs=2, feedback="explicit")
STATIC_CONFIG = {"feedback": "explicit"}

SEARCH_SPACE = {
    "max_nbrs": rt.randint(2, 50),
    "min_nbrs": rt.randint(1, 5),
    "min_sim": rt.loguniform(1e-6, 0.1),
}

TUNE_CPUS = "2"

DS_INCLUDE = ["ML1*"]
