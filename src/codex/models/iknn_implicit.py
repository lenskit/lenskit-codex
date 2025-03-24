import numpy as np
import ray.tune as rt
from lenskit.data import Dataset
from lenskit.knn import ItemKNNConfig, ItemKNNScorer
from lenskit.training import TrainingOptions

PREDICTOR = False
SCORER = ItemKNNScorer
DEFAULT_CONFIG = ItemKNNConfig(max_nbrs=10, min_nbrs=2, save_nbrs=10000, feedback="implicit")
STATIC_CONFIG = {"feedback": "implicit"}

SEARCH_SPACE = {
    "max_nbrs": rt.randint(2, 50),
    "min_nbrs": rt.randint(1, 5),
    "min_sim": rt.loguniform(1e-6, 0.1),
}
SEARCH_BASE_CONFIG = ItemKNNConfig(
    max_nbrs=10, save_nbrs=10000, min_sim=1.0e-6, feedback="implicit"
)

TUNE_CPUS = 2
OPTIONS = {"search_points": 60}


class TuningModelFactory:
    model: ItemKNNScorer | None = None

    def train(self, data: Dataset, options: TrainingOptions) -> ItemKNNScorer:
        self.model = ItemKNNScorer(SEARCH_BASE_CONFIG)
        self.model.train(data)
        return self.model

    def __call__(self, config: object) -> ItemKNNScorer:
        if self.model is None:
            return ItemKNNScorer(DEFAULT_CONFIG)

        shrunk = ItemKNNScorer(config)
        matrix = self.model.sim_matrix_.copy()
        matrix.data[matrix.data < shrunk.config.min_sim] = 0.0
        matrix.eliminate_zeros()
        shrunk.items_ = self.model.items_
        shrunk.users_ = self.model.users_
        shrunk.item_means_ = self.model.item_means_
        shrunk.item_counts_ = np.diff(matrix.indices)
        shrunk.sim_matrix_ = matrix
        return shrunk
