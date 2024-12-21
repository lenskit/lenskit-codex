"""
Explicit-feedback Item KNN.
"""

from lenskit.als import BiasedMF

outputs = ["recommendations", "predictions"]

sweep_space = {
    "features": [5, 10, 15, 25, 35, 50, 75, 100, 150, 250],
    "reg": [0.01, 0.1, 1.0],
}


def default():
    return BiasedMF(50)


def from_config(features, reg):
    return BiasedMF(features, reg=reg)
