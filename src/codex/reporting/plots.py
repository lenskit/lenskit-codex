"""
Plotting and display/output utilities for the codex.

Importing this module automatically sets up some defaults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import plotnine as pn
from humanize import naturalsize
from mizani.palettes import brewer_pal

if TYPE_CHECKING:
    from mizani.typing import RGBHexColor


class DisplayOptions(NamedTuple):
    line_color: RGBHexColor
    popint_color: RGBHexColor
    fill_color: RGBHexColor

    @classmethod
    def brewer(cls):
        dark2 = brewer_pal("qual", "Dark2")
        lc = dark2(2)[1]
        assert lc
        set2 = brewer_pal("qual", "Set2")
        fc = set2(2)[1]
        assert fc
        return cls(lc, lc, fc)


def init_plotting():
    pn.theme_set(pn.theme_classic() + pn.theme(figure_size=(7, 4), dpi=300))


def label_memory(xs):
    """
    Labeler (for Plotnine continous scale) for memory consumption.
    """
    return [naturalsize(x) for x in xs]


def scale_x_memory():
    return pn.scale_x_continuous(labels=label_memory)


def scale_y_memory():
    return pn.scale_y_continuous(labels=label_memory)


DEFAULTS = DisplayOptions.brewer()
init_plotting()
