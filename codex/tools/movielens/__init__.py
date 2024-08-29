from .. import codex


@codex.group()
def movielens():
    "Commands for manipulating MovieLens data."


from . import (  # noqa: E402, F401
    mlimport,
)
