"""
Explicit-feedback Item KNN.
"""

from lenskit.als import ImplicitMF

outputs = ["recommendations"]

sweep_space = {
    "features": [5, 10, 15, 25, 35, 50, 75, 100, 150, 250],
    "reg": [0.01, 0.1, 1.0],
}


def default():
    return ImplicitMF(50)


def from_config(features, reg):
    return ImplicitMF(features, reg=reg, use_ratings=False)
