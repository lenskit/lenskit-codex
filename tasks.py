import json
import os
import re
from glob import glob
from pathlib import Path

from invoke.context import Context
from invoke.tasks import task

from codex.layout import codex_root, load_data_info
from codex.pages import front_matter, render_templates
from codex.pipeline import render_dvc_gitignores, render_dvc_pipeline

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
    for file in glob("**/dvc.jsonnet", recursive=True):
        render_dvc_pipeline(file)

    c.run("dprint fmt '**/dvc.yaml'")


@task(render_pipeline)
def update_gitignore(c):
    render_dvc_gitignores()


@task(update_gitignore)
def rerender(c):
    print("Project layout updated")
