"""
DVC support utilities.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from fnmatch import fnmatch
from functools import partial
from glob import glob
from itertools import chain
from os import fspath
from pathlib import Path
from typing import Annotated, TypeAlias

import yaml
from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, JsonValue

from .layout import ROOT_DIR, DataSetInfo

logger = logging.getLogger(__name__)


class CodexPipeline:
    """
    Class representing the entire codex pipeline.
    """

    root: Path
    dir_pipes: dict[str, CodexPipelineDef]

    def __init__(self, root: Path = ROOT_DIR):
        self.root = root
        self.dir_pipes = {}

    def scan(self):
        """
        Scan and load the pipeline.
        """

        self.dir_pipes = {}
        for file in self.root.glob("**/dvc.jsonnet"):
            pipe = CodexPipelineDef.load_jsonnet(file)
            self._add_pipeline(file.parent, pipe)

    def _add_pipeline(self, path: Path, pipe: CodexPipelineDef):
        pstr = path.relative_to(self.root).as_posix()
        logger.debug("adding pipeline for %s", pstr)
        self.dir_pipes[pstr] = pipe
        pipe.path = pstr
        for sd, sdpipe in pipe.subdirs.items():
            self._add_pipeline(path / sd, sdpipe)

    def __iter__(self) -> Iterator[tuple[str, CodexPipelineDef]]:
        return iter(self.dir_pipes.items())


class DVCPipeline(BaseModel):
    stages: dict[str, DVCStage | DVCForeachStage]

    @classmethod
    def load_yaml(cls, path: Path):
        with open(path, "rt") as yf:
            data = yaml.safe_load(yf)
            return cls.model_validate(data)


class DVCOutOptions(BaseModel):
    cache: bool


DVCOut: TypeAlias = Annotated[dict[str, DVCOutOptions], MaxLen(1), MinLen(1)]


class DVCStage(BaseModel):
    cmd: str
    wdir: str | None = None
    deps: list[str] = []
    outs: list[str | DVCOut] = []
    metrics: list[str | DVCOut] = []
    params: list[str | dict[str, list[str]]] = []


class DVCForeachStage(BaseModel):
    foreach: list[str | dict[str, JsonValue]]
    do: DVCStage


class CodexPipelineDef(DVCPipeline):
    """
    Data loaded from a single pipeline definition file.
    """

    path: str | None = None
    info: DataSetInfo | None = None
    models: list[str] = []
    page_templates: Path | None = None
    subdirs: dict[str, CodexPipelineDef] = {}
    extra_files: dict[str, str | dict[str, JsonValue]] = {}

    @classmethod
    def load_jsonnet(cls, path: Path) -> CodexPipelineDef:
        import _jsonnet

        pdir = path.parent.absolute()
        logger.debug("evaluating JSONNet file %s", str(path))

        data = _jsonnet.evaluate_file(
            fspath(path),
            native_callbacks={
                "fnmatch": (("name", "pat"), fnmatch),
                "relpath": (
                    ("src", "tgt"),
                    lambda p1, p2: Path(p1).relative_to(p2, walk_up=True).as_posix(),
                ),
                "pipeline_dir": ((), lambda: pdir.relative_to(ROOT_DIR)),
                "project_root": ((), lambda: ROOT_DIR.relative_to(pdir, walk_up=True).as_posix()),
                "project_path": (
                    ("path",),
                    lambda path: (ROOT_DIR / path).relative_to(pdir, walk_up=True).as_posix(),
                ),
                "resolve_path": (("p1", "p2"), partial(_resolve_path, pdir)),
                "parse_path": (("path",), _parse_path),
                "glob": (("glob",), lambda g: [p.as_posix() for p in pdir.glob(g)]),
            },
        )
        return cls.model_validate_json(data)

    def render(self, dir: Path | None = None):
        logger.debug("rendering pipelines in %s", dir or self.path)
        self.save_dvc(dir)
        self.save_info(dir)
        self.save_extras(dir)

    def save_dvc(self, dir: Path | None = None):
        out = self._file_path("dvc.yaml", dir)
        logger.info("saving %s", out)
        with out.open("wt") as yf:
            print("# Codex Generated File — DO NOT EDIT", file=yf)
            print("#", file=yf)
            print("# This file is generated from dvc.jsonnet.", file=yf)

            yaml.safe_dump(
                self.dvc_object().model_dump(mode="yaml", exclude_unset=True, exclude_none=True), yf
            )

    def save_info(self, dir: Path | None = None):
        if self.info is not None:
            out = self._file_path("dataset.yml", dir)
            logger.debug("saving %s", out)
            with open(out, "wt") as yf:
                yaml.safe_dump(self.info.model_dump(mode="json"), yf)

    def save_extras(self, dir: Path | None = None):
        for name, content in self.extra_files.items():
            epath = self._file_path(name, dir)
            logger.debug("saving extra file %s", epath)
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

    def _file_path(self, name: str, dir: Path | None = None):
        if dir is None:
            if self.path is not None:
                dir = ROOT_DIR / self.path
            else:
                raise ValueError("no output path specified")
        return dir / name

    def dvc_object(self) -> DVCPipeline:
        """
        Get the object stripped down to its DVC content.
        """
        return DVCPipeline.model_validate(self.model_dump())


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
        dvc = Path(dvc)
        print("scanning", dvc, "for outputs")
        pl_dir = dvc.parent
        pipe = DVCPipeline.load_yaml(dvc)
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


def _parse_path(src: str):
    path = Path(src)
    return {
        "dir": path.parent.as_posix(),
        "name": path.name,
        "stem": path.stem,
        "suffix": path.suffix,
    }


def _resolve_path(base: Path, *paths: str):
    path = base
    for part in paths:
        path = path / part
    path = path.resolve()
    return path.relative_to(ROOT_DIR).as_posix()
