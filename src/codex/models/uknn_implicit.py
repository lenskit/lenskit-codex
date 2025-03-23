import ray.tune as rt
from lenskit.knn import UserKNNConfig, UserKNNScorer

PREDICTOR = False
SCORER = UserKNNScorer
DEFAULT_CONFIG = UserKNNConfig(max_nbrs=10, min_nbrs=2, feedback="implicit")
STATIC_CONFIG = {"feedback": "implicit"}

SEARCH_SPACE = {
    "max_nbrs": rt.randint(2, 50),
    "min_nbrs": rt.randint(1, 5),
    "min_sim": rt.loguniform(1e-6, 0.1),
}

TUNE_CPUS = "2"

OPTIONS = {"ds_include": ["ML1*"], "search_points": 60}
