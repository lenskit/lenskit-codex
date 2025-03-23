import ray.tune as rt
from lenskit.knn import ItemKNNConfig, ItemKNNScorer

PREDICTOR = False
SCORER = ItemKNNScorer
DEFAULT_CONFIG = ItemKNNConfig(max_nbrs=10, min_nbrs=2, save_nbrs=10000, feedback="implicit")
STATIC_CONFIG = {"feedback": "implicit"}

SEARCH_SPACE = {
    "max_nbrs": rt.randint(2, 50),
    "min_nbrs": rt.randint(1, 5),
    "min_sim": rt.loguniform(1e-6, 0.1),
}

TUNE_CPUS = "all"
OPTIONS = {"search_points": 60}
