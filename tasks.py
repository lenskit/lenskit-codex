import json
import re
import tomllib
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


@task
def list_models(c: Context):
    "List the available recommendation models."
    model_dir = Path("models")
    model_files = model_dir.glob("*.toml")

    models = {}
    for mf in model_files:
        spec = tomllib.loads(mf.read_text("utf8"))
        if spec.get("enabled", True):
            models[mf.stem] = {}

    with open("models/index.json", "wt") as jsf:
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
            for name, data in extras.items():
                epath = path.parent / name
                print("saving extra file", epath)
                epath.write_text(data)

        out = path.parent / "dvc.yaml"
        with out.open("wt") as yf:
            yaml.safe_dump(data, yf)

    c.run("dprint fmt '**/dvc.yaml'")
