import json
import logging
import os
import re
import sys
from glob import glob
from pathlib import Path

from invoke.context import Context
from invoke.tasks import task

from codex.layout import codex_root
from codex.pages import front_matter, render_templates
from codex.pipeline import (
    CodexPipeline,
    render_dvc_gitignores,
)

cdl = logging.getLogger("codex")
if not logging.root.handlers:
    _cdl_h = logging.StreamHandler(sys.stderr)
    _cdl_h.setLevel(logging.INFO)
    cdl.addHandler(_cdl_h)
    cdl.setLevel(logging.INFO)
logger = logging.getLogger("codex.tasks")

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
def render_page_templates(c: Context, include: str | None = None):
    "Render page templates."
    pipeline = CodexPipeline.instance()
    pipeline.scan()
    for pipe_dir, pipe in pipeline.defs():
        ds_dir = Path(pipe_dir)
        if pipe.page_templates:
            assert pipe.info is not None, "no info for pipeline"
            print("rendering templates for", ds_dir)
            render_templates(pipe.info, ds_dir / pipe.page_templates, ds_dir, include)


@task(render_page_templates)
def list_documents(c: Context):
    "List documents with their metadata."
    docs = glob("**/*.qmd", recursive=True)
    print("collecting", len(docs), "documents")
    docs = {name: front_matter(name) for name in sorted(docs) if not re.match(r".*/_", name)}

    with open("manifests/documents.json", "wt") as jsf:
        json.dump(docs, jsf, indent=2)
        print(file=jsf)

    CodexPipeline.instance().reset()


@task
def list_models(c: Context):
    "List the available recommendation models."
    from codex.config import get_config
    from codex.models import discover_models, load_model

    config = get_config()

    models = {}
    for mod_name in discover_models():
        mod = load_model(mod_name)
        models[mod.name] = {
            "src_path": f"src/codex/models/{mod.module_name}.py",
            "predictor": mod.is_predictor,
            "searchable": bool(mod.search_space),
        }
        models[mod.name].update(mod.options)
        for rule in config.models.include:
            if rule.matches_model(mod.name):
                if "ds_include" not in models[mod.name]:
                    models[mod.name]["ds_include"] = []
                models[mod.name]["ds_include"].append(rule.data)

    models = {k: models[k] for k in sorted(models.keys())}

    with open("manifests/models.json", "wt") as jsf:
        json.dump(models, jsf, indent=2)
        print(file=jsf)

    CodexPipeline.instance().reset()


@task(list_documents, list_models)
def render_pipeline(c: Context):
    pipeline = CodexPipeline.instance()
    pipeline.scan()

    for path, pipe in pipeline.defs():
        pipe.render()

    logger.info("formatting pipeline definitions")
    c.run("dprint fmt '**/dvc.yaml' '**/dataset.yml'")


@task(render_pipeline)
def update_gitignore(c):
    render_dvc_gitignores()


@task(update_gitignore)
def rerender(c):
    print("Project layout updated")
