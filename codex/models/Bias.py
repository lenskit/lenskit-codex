"""
Explicit-feedback Item KNN.
"""

from lenskit.algorithms.basic import Bias

outputs = ["recommendations", "predictions"]

sweep_space = {
    "user_damping": [0, 5, 10, 25],
    "item_damping": [0, 5, 10, 25],
}


def default():
    return Bias(damping=5)


def from_config(user_damping: float, item_damping: float):
    return Bias(damping=(user_damping, item_damping))
