"""
Explicit-feedback Item KNN.
"""

from lenskit.algorithms.user_knn import UserUser

outputs = ["recommendations"]

sweep_space = {
    "nnbrs": [5, 10, 15, 25, 35, 50],
    "min_nbrs": [1, 2],
}


def default():
    return UserUser(20, feedback="implicit")


def from_config(nnbrs, min_nbrs):
    return UserUser(nnbrs, min_nbrs=min_nbrs, feedback="implicit")
