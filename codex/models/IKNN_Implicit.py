"""
Explicit-feedback Item KNN.
"""

from lenskit.algorithms.item_knn import ItemItem

outputs = ["recommendations"]

sweep_space = {
    "nnbrs": [5, 10, 15, 25, 35, 50],
    "min_nbrs": [1, 2],
}


def default():
    return ItemItem(20, feedback="implicit")


def from_config(nnbrs, min_nbrs):
    return ItemItem(nnbrs, min_nbrs=min_nbrs, feedback="implicit")
