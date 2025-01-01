import { action_cmd, Stage } from "../src/dvc.ts";
import { MODELS } from "../src/pipeline/model-config.ts";

export function mlSweep(ds: string, split: string): Record<string, Stage> {
  const results: Record<string, Stage> = {};
  let split_dep = split == "random" ? "splits/random.duckdb" : `splits/${split}.toml`;
  let test_part = split == "random" ? "0" : "valid";
  for (const [name, info] of Object.entries(MODELS)) {
    if (info.search?.grid) {
      results[`sweep-${split}-grid-${name}`] = {
        cmd: action_cmd(
          "sweep run --grid",
          `--ds-name=${ds}`,
          `--split=splits/${split}.toml`,
          `--test-part=${test_part}`,
          name,
          `sweeps/${split}/${name}-grid`,
        ),
        params: [{ "../../config.toml": ["random.seed"] }],
        deps: [
          split_dep,
          "ratings.duckdb",
          `../../models/${name}.toml`,
        ],
        outs: [`sweeps/${split}/${name}-grid`],
      };
      const metric = info.predictor ? "RMSE" : "RBP";

      results[`export-${split}-${name}`] = {
        cmd: action_cmd(
          "sweep export",
          `-o sweeps/${split}/${name}-grid.json`,
          `sweeps/${split}/${name}-grid`,
          metric,
        ),
        deps: [`sweeps/${split}/${name}-grid`],
        outs: [
          { [`sweeps/${split}/${name}-grid.json`]: { cache: false } },
        ],
      };
    }

    if (info.search?.params) {
      results[`sweep-${split}-random-${name}`] = {
        cmd: action_cmd(
          "sweep run --random",
          `--ds-name=${ds}`,
          `--split=splits/${split}.toml`,
          `--test-part=${test_part}`,
          name,
          `sweeps/${split}/${name}-random`,
        ),
        params: [{ "../../config.toml": ["random.seed"] }],
        deps: [
          split_dep,
          "ratings.duckdb",
          `../../models/${name}.toml`,
        ],
        outs: [`sweeps/${split}/${name}-random`],
      };
      const metric = info.predictor ? "RMSE" : "RBP";

      results[`export-${split}-${name}`] = {
        cmd: action_cmd(
          "sweep export",
          `-o sweeps/${split}/${name}-random.json`,
          `sweeps/${split}/${name}-random`,
          metric,
        ),
        deps: [`sweeps/${split}/${name}-random`],
        outs: [
          { [`sweeps/${split}/${name}-random.json`]: { cache: false } },
        ],
      };
    }
  }

  return results;
}
