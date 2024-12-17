"""
Explicit-feedback Item KNN.
"""

from lenskit.knn import UserKNNScorer

outputs = ["recommendations", "predictions"]

sweep_space = {
    "nnbrs": [5, 10, 15, 25, 35, 50],
    "min_nbrs": [1, 2],
}


def default():
    return UserKNNScorer(20, feedback="explicit")


def from_config(nnbrs, min_nbrs):
    return UserKNNScorer(nnbrs, min_nbrs=min_nbrs, feedback="explicit")
