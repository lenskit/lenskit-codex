import json
import os
import re
from glob import glob
from pathlib import Path

import yaml
from invoke.context import Context
from invoke.tasks import task

from codex.layout import codex_root, load_data_info
from codex.pages import front_matter, render_templates

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
def render_page_templates(c: Context):
    "Render page templates."
    ds_yamls = glob("**/dataset.yml", recursive=True)
    for dsy in ds_yamls:
        dsy = Path(dsy)
        ds_dir = dsy.parent
        ds = load_data_info(ds_dir)
        if ds.template:
            print("rendering templates for", ds_dir)
            render_templates(ds, ds_dir / ds.template, ds_dir)


@task
def list_documents(c: Context):
    "List documents with their metadata."
    docs = glob("**/*.qmd", recursive=True)
    print("collecting", len(docs), "documents")
    docs = {name: front_matter(name) for name in docs if not re.match(r".*/_", name)}

    with open("manifests/documents.json", "wt") as jsf:
        json.dump(docs, jsf, indent=2)
        print(file=jsf)


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


@task(render_pipeline)
def update_gitignore(c):
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


@task(update_gitignore)
def rerender(c):
    print("Project layout updated")
