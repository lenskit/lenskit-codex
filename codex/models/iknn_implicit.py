"""
Explicit-feedback Item KNN.
"""

from lenskit.algorithms.knn.item import ItemItem

outputs = ["recommendations"]

sweep_space = {
    "nnbrs": [5, 10, 15, 25, 35, 50],
    "min_nbrs": [1, 2],
}
