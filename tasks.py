import json
import re
from glob import glob
from pathlib import Path

import yaml
from invoke.context import Context
from invoke.tasks import task


@task
def render(c: Context):
    "Render the website."
    c.run("quarto render --to html")


@task
def upload_web_assets(c: Context):
    "Upload the web assets."
    c.run("dvc push --no-run-cache -r public dvc.yaml")
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
    docs = {name: _front_matter(name) for name in docs}

    with open("documents.json", "wt") as jsf:
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


@task(list_documents)
def render_pipeline(c: Context):
    import _jsonnet

    for file in glob("**/dvc.jsonnet", recursive=True):
        path = Path(file)
        print("rendering", file)
        data = _jsonnet.evaluate_file(file)
        data = json.loads(data)
        out = path.parent / "dvc.yaml"
        with out.open("wt") as yf:
            yaml.safe_dump(data, yf)

    c.run("dprint fmt '**/dvc.yaml'")
