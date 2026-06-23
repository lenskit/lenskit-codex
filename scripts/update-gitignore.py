#!/usr/bin/env python
"""
Update gitignore files.
"""

from __future__ import annotations

import logging
import re
from glob import glob
from itertools import chain
from pathlib import Path
from typing import Annotated, TypeAlias

from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, JsonValue
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


def main():
    render_dvc_gitignores()


class DVCPipeline(BaseModel):
    stages: dict[str, DVCStage | DVCForeachStage]

    @classmethod
    def load_yaml(cls, path: Path):
        with open(path, "rt") as yf:
            yaml = YAML(typ="safe")
            data = yaml.load(yf)
            return cls.model_validate(data)


class DVCOutOptions(BaseModel):
    cache: bool


DVCOut: TypeAlias = Annotated[dict[str, DVCOutOptions], MaxLen(1), MinLen(1)]


class DVCStage(BaseModel):
    cmd: str
    wdir: str | None = None
    params: list[str | dict[str, list[str]]] = []
    deps: list[str] = []
    outs: list[str | DVCOut] = []
    metrics: list[str | DVCOut] = []


class DVCForeachStage(BaseModel):
    foreach: list[str | dict[str, JsonValue]]
    do: DVCStage


def render_dvc_gitignores():
    root = Path().resolve()
    ignores = {}

    for gi in glob("**/.gitignore", recursive=True, include_hidden=False):
        gi_dir = Path(gi).parent.as_posix()
        with open(gi, "rt") as gif:
            ignores[gi_dir] = set(
                line.strip() for line in gif if not re.match(r"^\s*(#.*)?$", line)
            )

    for file in root.glob("**/dvc.yaml"):
        pl_dir = file.parent
        pipe = DVCPipeline.load_yaml(file)

        print("scanning", pl_dir, "for outputs")
        for stage in pipe.stages.values():
            if not isinstance(stage, DVCStage):
                # we ignore foreach stages
                continue

            wdp = pl_dir if stage.wdir is None else pl_dir / stage.wdir
            wdp = wdp.resolve()
            for out in chain(stage.outs, stage.metrics):
                if not isinstance(out, str):
                    continue

                out_p = wdp / out
                out_p = out_p.resolve().relative_to(root)

                out_dir = out_p.parent.as_posix()
                out_ign = ignores.setdefault(out_dir, set())
                out_ign.add("/" + out_p.name)

    for d, ign in ignores.items():
        fn = Path(d) / ".gitignore"
        fn.parent.mkdir(exist_ok=True, parents=True)
        print("writing", fn)
        with fn.open("wt") as gif:
            for f in sorted(ign):
                print(f, file=gif)


if __name__ == "__main__":
    main()
