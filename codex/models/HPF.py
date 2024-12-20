"""
HPF from the hpfrec library.
"""

from lenskit.hpf import HPF

outputs = ["recommendations"]

sweep_space = {
    "features": [5, 10, 15, 25, 35, 50, 75, 100, 150, 250],
}


def default():
    return HPF(50)


def from_config(features):
    return HPF(features)
