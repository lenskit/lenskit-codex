"""
DVC support utilities.
"""

from __future__ import annotations

import json
import logging
import re
from glob import glob
from os import fspath
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def render_dvc_pipeline(path: Path | str):
    import _jsonnet

    path = Path(path)
    print("rendering", path)
    data = _jsonnet.evaluate_file(fspath(path))
    data = json.loads(data)

    if extras := data.get("extraFiles", None):
        del data["extraFiles"]
        for name, content in extras.items():
            epath = path.parent / name
            print("saving extra file", epath)
            epath.write_text(content)

    out = path.parent / "dvc.yaml"
    with out.open("wt") as yf:
        yaml.safe_dump(data, yf)


def render_dvc_gitignores():
    root = Path().resolve()
    ignores = {}
    for gi in glob("**/.gitignore", recursive=True, include_hidden=False):
        gi_dir = Path(gi).parent.as_posix()
        with open(gi, "rt") as gif:
            ignores[gi_dir] = set(
                line.strip() for line in gif if not re.match(r"^\s*(#.*)?$", line)
            )

    for dvc in glob("**/dvc.yaml", recursive=True, include_hidden=False):
        print("scanning", dvc, "for outputs")
        pl_dir = Path(dvc).parent
        with open(dvc, "rt") as yf:
            pipe = yaml.safe_load(yf)
        stages = pipe["stages"]
        for stage in stages.values():
            wdir = stage.get("wdir", None)
            wdp = pl_dir if wdir is None else pl_dir / wdir
            wdp = wdp.resolve()
            for out in stage.get("outs", []):
                if not isinstance(out, str):
                    continue

                out_p = wdp / out
                out_p = out_p.resolve().relative_to(root)

                out_dir = out_p.parent.as_posix()
                if out_dir not in ignores:
                    ignores[out_dir] = set()
                ignores[out_dir].add("/" + out_p.name)

    for d, ign in ignores.items():
        fn = Path(d) / ".gitignore"
        print("writing", fn)
        with fn.open("wt") as gif:
            for f in sorted(ign):
                print(f, file=gif)
