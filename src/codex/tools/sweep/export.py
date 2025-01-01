import json
from pathlib import Path

import click
import pandas as pd
from lenskit.logging import get_logger

from . import sweep

_log = get_logger(__name__)


@sweep.command("export")
@click.option("-o", "--output", type=Path, metavar="FILE", help="write output to FILE")
@click.argument("SWEEP", type=Path)
@click.argument("METRIC")
def export_best_results(sweep: Path, metric: str, output: Path):
    log = _log.bind(results=str(sweep))
    order = "ASC" if metric in ("RMSE", "MAE") else "DESC"

    log.info("reading runs.json")
    run_file = sweep / "runs.json"
    data = pd.read_json(run_file, lines=True)

    run_ids = data["run_id"]
    params = pd.json_normalize(data["params"].tolist()).assign(run_id=run_ids).set_index("run_id")
    metrics = pd.json_normalize(data["metrics"].tolist()).assign(run_id=run_ids).set_index("run_id")

    if order == "DESC":
        top = metrics.nlargest(5, metric)
        print(top)
    else:
        top = metrics.nsmallest(5, metric)

    log.info("best results:\n%s", top.join(params, how="left"))

    params = params.to_dict("index")

    best_id = top.index[0]
    best = {
        "run_id": best_id,
        "metrics": metrics.loc[best_id].to_dict(),
        "params": params[best_id],
    }
    log.info("found best configuration", config=best)

    output.parent.mkdir(exist_ok=True, parents=True)
    output.write_text(json.dumps(best) + "\n")
