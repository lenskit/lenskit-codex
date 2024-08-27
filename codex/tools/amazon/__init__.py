from .. import codex


@codex.group()
def amazon():
    "Commands for manipulating Amazon data."


from . import (  # noqa: E402, F401
    collect_ids,
    import_bench,
)
