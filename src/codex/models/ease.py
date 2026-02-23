import ray.tune as rt
from lenskit.knn import EASEConfig, EASEScorer

SCORER = EASEScorer
DEFAULT_CONFIG = EASEConfig(damping=50)

SEARCH_SPACE = {"regularization": rt.loguniform(0.01, 1000)}
