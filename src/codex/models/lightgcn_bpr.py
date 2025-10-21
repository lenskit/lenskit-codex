import ray.tune as rt
import torch
from lenskit.graphs import LightGCNConfig, LightGCNScorer

PREDICTOR = False
SCORER = LightGCNScorer
DEFAULT_CONFIG = LightGCNConfig(loss="pairwise")
STATIC_CONFIG = {"loss": "pairwise"}

# SEARCH_SPACE = {
#     "embedding_size_exp": rt.randint(3, 10),
#     "layer_count": rt.randint(1, 3),
#     "regularization": rt.loguniform(1e-4, 10),
#     "learning_rate": rt.loguniform(1e-3, 1e-1),
# }

OPTIONS = {"max_epochs": 50}
# we can train on CPU, it's just slower
if torch.cuda.is_available():
    TUNE_GPUS = 0.5
