"""
DVC support utilities.
"""

from __future__ import annotations

import json
import logging
import re
from fnmatch import fnmatch
from glob import glob
from os import fspath
from pathlib import Path

import yaml
from pydantic import BaseModel, JsonValue

from .layout import DataSetInfo

logger = logging.getLogger(__name__)


class DVCPipeline(BaseModel):
    stages: dict[str, JsonValue]


class CodexPipeline(DVCPipeline):
    info: DataSetInfo | None = None
    models: list[str] = []
    page_templates: Path | None = None
    extra_files: dict[str, str | dict[str, JsonValue]] = {}

    @classmethod
    def load(cls, path: Path) -> CodexPipeline:
        import _jsonnet

        data = _jsonnet.evaluate_file(
            fspath(path), native_callbacks={"fnmatch": (("name", "pat"), fnmatch)}
        )
        return cls.model_validate_json(data)

    def dvc_object(self) -> DVCPipeline:
        """
        Get the object stripped down to its DVC content.
        """
        return DVCPipeline.model_validate(self.model_dump())


def render_dvc_pipeline(path: Path | str):
    path = Path(path)
    print("rendering", path)
    pipeline = CodexPipeline.load(path)

    for name, content in pipeline.extra_files.items():
        epath = path.parent / name
        print("saving extra file", epath)
        epath.parent.mkdir(exist_ok=True, parents=True)
        with open(epath, "wt") as ef:
            if isinstance(content, dict):
                if re.match(r"\.ya?ml", epath.suffix):
                    yaml.safe_dump(content, ef)
                elif epath.suffix == ".json":
                    json.dump(content, ef)
                    print(file=ef)
                else:
                    raise ValueError(f"unknown file type {epath.suffix} for object data")
            elif isinstance(content, str):
                ef.write(content)
            else:
                raise TypeError(f"unsupported content type {type(content)}")

    out = path.parent / "dvc.yaml"
    with out.open("wt") as yf:
        yaml.safe_dump(pipeline.dvc_object().model_dump(mode="yaml", exclude_unset=True), yf)

    if pipeline.info is not None:
        with open(path.parent / "dataset.yml", "wt") as yf:
            yaml.safe_dump(pipeline.info.model_dump(mode="json"), yf)


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
        fn.parent.mkdir(exist_ok=True, parents=True)
        print("writing", fn)
        with fn.open("wt") as gif:
            for f in sorted(ign):
                print(f, file=gif)
