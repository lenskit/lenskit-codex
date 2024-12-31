import { filterValues } from "std/collections/mod.ts";

import { action_cmd, Stage } from "../src/dvc.ts";
import { MODELS } from "../src/pipeline/model-config.ts";

export function mlSweep(ds: string, split: string): Record<string, Stage> {
  const active = filterValues(MODELS, (m) => m.grid != null);
  const results: Record<string, Stage> = {};
  let split_dep = split == "random" ? "splits/random.duckdb" : `splits/${split}.toml`;
  let test_part = split == "random" ? "0" : "valid";
  for (const [name, info] of Object.entries(active)) {
    results[`sweep-${split}-${name}`] = {
      cmd: action_cmd(
        "sweep run",
        `--ds-name=${ds}`,
        `--split=splits/${split}.toml`,
        `--test-part=${test_part}`,
        name,
        `sweeps/${split}/${name}`,
      ),
      params: [{ "../../config.toml": ["random.seed"] }],
      deps: [
        split_dep,
        "ratings.duckdb",
        `../../models/${name}.toml`,
      ],
      outs: [`sweeps/${split}/${name}`],
    };
    const metric = info.predictor ? "RMSE" : "RBP";
    results[`export-${split}-${name}`] = {
      cmd: action_cmd(
        "sweep export",
        `-o sweeps/${split}/${name}.json`,
        `sweeps/${split}/${name}`,
        metric,
      ),
      deps: [`sweeps/${split}/${name}`],
      outs: [
        { [`sweeps/${split}/${name}.json`]: { cache: false } },
      ],
    };
  }

  return results;
}
