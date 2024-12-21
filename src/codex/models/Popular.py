"""
Explicit-feedback Item KNN.
"""

from lenskit.basic import PopScorer

outputs = ["recommendations"]

sweep_space = {}


def default():
    return PopScorer()


def from_config():
    raise NotImplementedError()
