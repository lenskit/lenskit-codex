"""
Explicit-feedback Item KNN.
"""

from lenskit.basic import BiasScorer

outputs = ["recommendations", "predictions"]

sweep_space = {
    "user_damping": [0, 5, 10, 25],
    "item_damping": [0, 5, 10, 25],
}


def default():
    return BiasScorer(damping=5)


def from_config(user_damping: float, item_damping: float):
    return BiasScorer(damping=(user_damping, item_damping))
