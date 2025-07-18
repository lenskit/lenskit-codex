"""
Distribution fitting support.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeAlias

import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as sps
from numpy.typing import NDArray
from scipy.special import rel_entr
from tabulate import tabulate

DistSpec: TypeAlias = tuple[
    str, sps.rv_continuous | sps.rv_discrete, dict[str, tuple[float, float]]
]


class DistributionSet:
    specs: list[DistSpec]
    fits: dict[str, Any]
    quality_kl: dict[str, float]
    quality_js: dict[str, float]
    data: NDArray[np.number]
    range: tuple[float, float]

    def __init__(self, specs: list[DistSpec]):
        self.specs = specs

    def fit(self, data: NDArray[np.number]):
        """
        Fit the distributions to the specified data
        """
        self.data = data
        self.fits = {name: sps.fit(dist, data, space).params for name, dist, space in self.specs}  # type: ignore
        self.range = (data.min(), data.max())
        self.quality_kl = {n: div_kl(data, dist, fit) for n, dist, fit in self.dist_fits()}
        self.quality_js = {n: dist_js(data, dist, fit) for n, dist, fit in self.dist_fits()}

    def dist_fits(self):
        for name, dist, _space in self.specs:
            fit = self.fits[name]
            yield name, dist, fit

    def table(self):
        """
        Display a table of the data.
        """
        return tabulate(
            [
                (
                    name,
                    ", ".join(
                        [
                            f"`{n}`={v:.3f}"
                            for n, v in fit._asdict().items()
                            if n not in ("loc", "scale")
                        ]
                    ),
                    f"{fit.loc:.3f}" if hasattr(fit, "loc") else "",
                    f"{fit.scale:.3f}" if hasattr(fit, "scale") else "",
                    f"{self.quality_kl[name]:.3f}",
                    f"{self.quality_js[name]:.3f}",
                )
                for name, dist, fit in self.dist_fits()
            ],
            headers=["Distribution", "Params", "Location", "Scale", "D(KL)", "Δ(JS)"],
        )

    def plot(self):
        lb, ub = self.range
        xs = np.logspace(np.log10(max(lb, 1)), np.log10(ub), 500, base=10)
        plt.ecdf(self.data, color="black", label="Empirical")
        for name, dist, fit in self.dist_fits():
            plt.plot(xs, dist.cdf(xs, *fit), linestyle="dashed", label=name)
        plt.xscale("symlog")
        plt.legend()


def div_kl(xs: NDArray[np.number], dist: sps.rv_discrete | sps.rv_continuous, params) -> float:
    """
    Quantify goodness-of-fit with K-L divergence.
    """

    uvs, counts = np.unique_counts(xs)
    lb = uvs.min()
    ub = uvs.max()
    rng = ub - lb

    p_probs = np.zeros(rng + 1)
    p_probs[uvs - lb] = counts / np.sum(counts)

    q_vs = np.arange(lb, ub + 1)
    if hasattr(dist, "pmf"):
        q_probs = dist.pmf(q_vs, *params)
    else:
        q_probs = dist.cdf(q_vs + 0.5, *params) - dist.cdf(q_vs - 0.5, *params)

    return rel_entr(p_probs, q_probs).sum()


def dist_js(xs: NDArray[np.number], dist: sps.rv_discrete | sps.rv_continuous, params) -> float:
    """
    Quantify goodness-of-fit with Jenson-Shannon distance.
    """

    uvs, counts = np.unique_counts(xs)
    lb = uvs.min()
    ub = uvs.max()
    rng = ub - lb

    p_probs = np.zeros(rng + 1)
    p_probs[uvs - lb] = counts / np.sum(counts)

    q_vs = np.arange(lb, ub + 1)
    if hasattr(dist, "pmf"):
        q_probs = dist.pmf(q_vs, *params)
    else:
        q_probs = dist.cdf(q_vs + 0.5, *params) - dist.cdf(q_vs - 0.5, *params)

    m_probs = q_probs + p_probs
    m_probs *= 0.5

    p_kl = rel_entr(p_probs, m_probs).sum()
    q_kl = rel_entr(q_probs, m_probs).sum()
    js_div = p_kl + q_kl
    js_div *= 0.5

    return np.sqrt(js_div)
