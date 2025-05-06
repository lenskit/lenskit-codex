import numpy as np
import ray.tune as rt
from lenskit.data import Dataset
from lenskit.data.matrix import SparseRowArray
from lenskit.knn import ItemKNNConfig, ItemKNNScorer
from lenskit.training import TrainingOptions

PREDICTOR = True
SCORER = ItemKNNScorer
DEFAULT_CONFIG = ItemKNNConfig(max_nbrs=20, min_nbrs=2, save_nbrs=10000, feedback="explicit")
STATIC_CONFIG = {"feedback": "explicit"}

SEARCH_SPACE = {
    "max_nbrs": rt.randint(2, 50),
    "min_nbrs": rt.randint(1, 5),
    "min_sim": rt.loguniform(1e-6, 0.1),
}
# a base configuration that con cover the whole search space
SEARCH_BASE_CONFIG = ItemKNNConfig(
    max_nbrs=20, save_nbrs=10000, min_sim=1.0e-6, feedback="explicit"
)


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
        matrix = self.model.sim_matrix.to_scipy().copy()
        matrix.data[matrix.data < shrunk.config.min_sim] = 0.0
        matrix.eliminate_zeros()
        shrunk.items = self.model.items
        shrunk.item_means = self.model.item_means
        shrunk.item_counts = np.diff(matrix.indices)
        shrunk.sim_matrix = SparseRowArray.from_scipy(matrix, large=True)
        return shrunk
