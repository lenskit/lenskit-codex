"""
Plotting and display/output utilities for the codex.

Importing this module automatically sets up some defaults.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import plotnine as pn
from mizani.palettes import brewer_pal

if TYPE_CHECKING:
    from mizani.typing import RGBHexColor


class DisplayOptions(NamedTuple):
    line_color: RGBHexColor
    fill_color: RGBHexColor

    @classmethod
    def brewer(cls):
        dark2 = brewer_pal("qual", "Dark2")
        lc = dark2(2)[1]
        assert lc
        set2 = brewer_pal("qual", "Set2")
        fc = set2(2)[1]
        assert fc
        return cls(lc, fc)


def init_plotting():
    pn.theme_set(pn.theme_classic() + pn.theme(figure_size=(7, 4), dpi=300))


DEFAULTS = DisplayOptions.brewer()
init_plotting()
