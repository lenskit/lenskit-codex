import numpy as np
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


class ReusableTuningModel:
    base_config = ItemKNNConfig(
        max_nbrs=20, min_nbrs=2, save_nbrs=10000, min_sim=1.0e-6, feedback="explicit"
    )

    def base_model(self) -> ItemKNNScorer:
        return ItemKNNScorer(self.base_config)

    def adapt_model(self, base: ItemKNNScorer, config: ItemKNNConfig) -> ItemKNNScorer:
        shrunk = ItemKNNScorer(config)
        matrix = base.sim_matrix_.copy()
        matrix.data[matrix.data < config.min_sim] = 0.0
        matrix.eliminate_zeros()
        shrunk.items_ = base.items_
        shrunk.users_ = base.users_
        shrunk.item_means_ = base.item_means_
        shrunk.item_counts_ = np.diff(matrix.indices)
        shrunk.sim_matrix_ = matrix
