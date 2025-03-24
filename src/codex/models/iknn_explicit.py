import numpy as np
import ray.tune as rt
from lenskit.knn import ItemKNNConfig, ItemKNNScorer

PREDICTOR = True
SCORER = ItemKNNScorer
DEFAULT_CONFIG = ItemKNNConfig(max_nbrs=20, min_nbrs=2, save_nbrs=10000, feedback="explicit")
STATIC_CONFIG = {"feedback": "explicit"}

SEARCH_SPACE = {
    "max_nbrs": rt.randint(2, 50),
    "min_nbrs": rt.randint(1, 5),
    "min_sim": rt.loguniform(1e-6, 0.1),
}

TUNE_CPUS = "all"
OPTIONS = {"search_points": 60}

SEARCH_BASE_CONFIG = ItemKNNConfig(
    max_nbrs=20, min_nbrs=2, save_nbrs=10000, min_sim=1.0e-6, feedback="explicit"
)


def search_adapt(model: ItemKNNScorer, config: ItemKNNConfig):
    shrunk = ItemKNNScorer(config)
    matrix = model.sim_matrix_.copy()
    matrix.data[matrix.data < config.min_sim] = 0.0
    matrix.eliminate_zeros()
    shrunk.items_ = model.items_
    shrunk.users_ = model.users_
    shrunk.item_means_ = model.item_means_
    shrunk.item_counts_ = np.diff(matrix.indices)
    shrunk.sim_matrix_ = matrix
