"""
BPR from the Implicit library.
"""

from lenskit.implicit import BPR

outputs = ["recommendations"]

sweep_space = {
    "features": [5, 10, 15, 25, 35, 50, 75, 100, 150, 250],
    "regularization": [0.01, 0.1, 1.0],
}


def default():
    return BPR(50)


def from_config(features, regularization):
    return BPR(features, regularization=regularization)
