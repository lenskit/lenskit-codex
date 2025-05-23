import logging
import re
from pathlib import Path

from ruamel.yaml import YAML

from codex.layout import DataSetInfo

logger = logging.getLogger(__name__)


def front_matter(path: Path | str | None = None, *, text: str | None = None):
    if text is None:
        logger.debug("loading %s for front matter", path)
        if path is None:
            raise RuntimeError("must specify path or text")
        path = Path(path)
        text = path.read_text("utf8")

    if m := re.match(r"^---+\s*\n(.*?)\n---+", text, re.DOTALL):
        logger.debug("found metadata")
        yaml = YAML(typ="safe")
        return yaml.load(m.group(1))
    else:
        return {}


def render_templates(ds: DataSetInfo, src: Path, dst: Path, glob: str | None = None):
    "Render page templates."
    import jinja2

    if not src.exists():
        raise FileNotFoundError(src.as_posix())

    loader = jinja2.FileSystemLoader(src)
    env = jinja2.Environment(autoescape=False, loader=loader)
    for file in src.glob("*.qmd"):
        if glob is not None and not file.match(glob):
            continue

        logger.debug("rendering document %s to %s", file.name, dst)
        tmpl = env.get_template(file.name)
        res = tmpl.render(ds=ds)
        if res[-1] != "\n":
            res += "\n"

        meta = front_matter(text=res)
        if mod := meta.get("model"):
            if mod not in ds.models:
                logger.debug("skipping document %s for %s", file.name, dst)
                continue

        logger.debug("saving document %s to %s", file.name, dst)
        out_file = dst / file.name
        out_tmp = dst / f".{file.name}.tmp"
        out_tmp.write_text(res)
        out_tmp.rename(out_file)
