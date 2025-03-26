import json
import os
import re
from glob import glob
from pathlib import Path

import yaml
from invoke.context import Context
from invoke.tasks import task

from codex.layout import codex_root

os.chdir(codex_root())


@task
def render_site(c: Context):
    "Render the website."
    c.run("quarto render --to html")


@task
def upload_web_assets(c: Context):
    "Upload the web assets."
    print("pushing page outputs")
    c.run("dvc push --no-run-cache -r public dvc.yaml")
    print("pushing static images")
    c.run("dvc push --no-run-cache -r public -R images")


@task
def fetch_web_assets(c: Context):
    "Fetch the web assets."
    c.run("dvc pull --no-run-cache -r public dvc.yaml")
    c.run("dvc pull --no-run-cache -r public -R images")


@task
def list_documents(c: Context):
    "List documents with their metadata."
    docs = glob("**/*.qmd", recursive=True)
    print("collecting", len(docs), "documents")
    docs = {name: _front_matter(name) for name in docs if not re.match(r"/_", name)}

    with open("manifests/documents.json", "wt") as jsf:
        json.dump(docs, jsf, indent=2)
        print(file=jsf)


def _front_matter(path):
    path = Path(path)
    text = path.read_text("utf8")
    if m := re.match(r"^---+\s*\n(.*?)\n---+", text, re.DOTALL):
        print("found metadata in", path)
        return yaml.safe_load(m.group(1))
    else:
        return {}


@task
def list_models(c: Context):
    "List the available recommendation models."
    from codex.models import discover_models, load_model

    models = {}
    for mod_name in discover_models():
        mod = load_model(mod_name)
        models[mod.name] = {
            "src_path": f"src/codex/models/{mod.module_name}.py",
            "predictor": mod.is_predictor,
            "searchable": bool(mod.search_space),
        }
        models[mod.name].update(mod.options)

    with open("manifests/models.json", "wt") as jsf:
        json.dump(models, jsf, indent=2)
        print(file=jsf)


@task(list_documents, list_models)
def render_pipeline(c: Context):
    import _jsonnet

    for file in glob("**/dvc.jsonnet", recursive=True):
        path = Path(file)
        print("rendering", file)
        data = _jsonnet.evaluate_file(file)
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

    c.run("dprint fmt '**/dvc.yaml'")


@task
def render_gitignore(c):
    root = Path().resolve()
    ignores = {}
    for gi in glob("**/.gitignore", recursive=True, include_hidden=False):
        gi_dir = Path(gi).parent.as_posix()
        with open(gi, "rt") as gif:
            ignores[gi_dir] = set(
                line.strip() for line in gif if not re.match(r"^\s*(#.*)?$", line)
            )

    for dvc in glob("**/dvc.yaml", recursive=True, include_hidden=False):
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
        with fn.open("wt") as gif:
            for f in sorted(ign):
                print(f, file=gif)
