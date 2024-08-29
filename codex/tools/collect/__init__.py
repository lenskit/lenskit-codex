from .. import codex


@codex.group("collect")
def collect():
    "Commands for collecting metrics and other data."


from . import (  # noqa: E402, F401
    metrics,
)
