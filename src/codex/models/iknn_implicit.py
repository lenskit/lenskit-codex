import numpy as np
import ray.tune as rt
from lenskit.data import Dataset
from lenskit.data.matrix import SparseRowArray
from lenskit.knn import ItemKNNConfig, ItemKNNScorer
from lenskit.training import TrainingOptions
from scipy.sparse import csr_array

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
        m2 = self.model.sim_matrix.to_scipy().tocoo()
        mask = m2.data >= shrunk.config.min_sim
        matrix = csr_array((m2.data[mask], (m2.row[mask], m2.col[mask])), shape=m2.shape)
        shrunk.items = self.model.items
        shrunk.item_means = self.model.item_means
        shrunk.item_counts = np.diff(matrix.indices)
        shrunk.sim_matrix = SparseRowArray.from_scipy(matrix, large=True)
        return shrunk
