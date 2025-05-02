import logging
import re
from pathlib import Path

import yaml

from codex.layout import DataSetInfo

logger = logging.getLogger(__name__)


def front_matter(path: Path | str):
    path = Path(path)
    text = path.read_text("utf8")
    if m := re.match(r"^---+\s*\n(.*?)\n---+", text, re.DOTALL):
        print("found metadata in", path)
        return yaml.safe_load(m.group(1))
    else:
        return {}


def render_templates(ds: DataSetInfo, src: Path, dst: Path):
    "Render page templates."
    import jinja2

    if not src.exists():
        raise FileNotFoundError(src.as_posix())

    loader = jinja2.FileSystemLoader(src)
    env = jinja2.Environment(autoescape=False, loader=loader)
    for file in src.glob("*.qmd"):
        logger.info("rendering document %s to %s", file.name, dst)
        tmpl = env.get_template(file.name)
        res = tmpl.render(ds=ds)
        if res[-1] != "\n":
            res += "\n"
        out_file = dst / file.name
        out_file.write_text(res)
