import ray.tune as rt
import torch
from lenskit.flexmf import FlexMFExplicitConfig, FlexMFExplicitScorer

PREDICTOR = True
SCORER = FlexMFExplicitScorer
DEFAULT_CONFIG = FlexMFExplicitConfig()

SEARCH_SPACE = {
    "embedding_size_exp": rt.randint(3, 10),
    "regularization": rt.loguniform(1e-4, 10),
    "learning_rate": rt.loguniform(1e-3, 1e-1),
    "reg_method": rt.choice(["L2", "AdamW"]),
}

OPTIONS = {"max_epochs": 50}
# we can train on CPU, it's just slower
if torch.cuda.is_available():
    TUNE_GPUS = 0.2
