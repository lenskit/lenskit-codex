import ray.tune as rt
import torch
from lenskit.flexmf import FlexMFImplicitConfig, FlexMFImplicitScorer

PREDICTOR = False
SCORER = FlexMFImplicitScorer
DEFAULT_CONFIG = FlexMFImplicitConfig(loss="warp")
STATIC_CONFIG = {"loss": "warp"}

SEARCH_SPACE = {
    "embedding_size": rt.lograndint(4, 512, base=2),
    "regularization": rt.loguniform(1e-4, 10),
    "learning_rate": rt.loguniform(1e-3, 1e-1),
    "reg_method": rt.choice(["L2", "AdamW"]),
    # "negative_count": rt.randint(1, 5),
    "item_bias": rt.choice([True, False]),
}

OPTIONS = {"max_epochs": 50}
# we can train on CPU, it's just slower
if torch.cuda.is_available():
    TUNE_GPUS = 0.2
