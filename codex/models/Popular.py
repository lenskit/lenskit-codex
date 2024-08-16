"""
Explicit-feedback Item KNN.
"""

from lenskit.algorithms.basic import PopScore

outputs = ["recommendations"]

sweep_space = {}


def default():
    return PopScore()


def from_config():
    raise NotImplementedError()
