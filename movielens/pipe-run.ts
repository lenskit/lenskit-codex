import { action_cmd, Stage } from "../src/dvc.ts";
import { MODELS } from "../src/pipeline/model-config.ts";

export function mlCrossfoldRuns(ds: string, split: string): Record<string, Stage> {
  const runs: Record<string, Stage> = {};

  for (const [name, info] of Object.entries(MODELS)) {
    runs[`run-${split}-default-${name}`] = {
      cmd: action_cmd(
        `movielens/${ds}`,
        "generate",
        "--default",
        `--split=splits/${split}.toml`,
        "--test-part=-0",
        `-o runs/${split}-default/${name}`,
        name,
      ),
      outs: [`runs/${split}-default/${name}`],
      deps: [
        `../../models/${name}.toml`,
        "ratings.duckdb",
        `splits/${split}.duckdb`,
      ],
    };

    if (info.sweep == null) continue;

    runs[`run-${split}-sweep-best-${name}`] = {
      cmd: action_cmd(
        `movielens/${name}`,
        "generate",
        `--param-file=sweeps/${split}/${name}.json`,
        `--split=splits/${split}.toml`,
        "--test-part=-0",
        `-o runs/${split}-sweep-best/${name}`,
        name,
      ),
      outs: [`runs/${split}-sweep-best/${name}`],
      deps: [
        `../../models/${name}.toml`,
        "ratings.duckdb",
        `splits/${split}.duckdb`,
        `sweeps/${split}/${name}.json`,
      ],
    };
  }

  return runs;
}

export function mlSplitRuns(ds: string, split: string): Record<string, Stage> {
  const runs: Record<string, Stage> = {};

  for (const [name, info] of Object.entries(MODELS)) {
    runs[`run-${split}-valid-default-${name}`] = {
      cmd: action_cmd(
        `movielens/${ds}`,
        "generate",
        "--default",
        `--split=splits/${split}.toml`,
        "--test-part=valid",
        `-o runs/${split}-valid-default/${name}`,
        name,
      ),
      outs: [`runs/${split}-valid-default/${name}`],
      deps: [
        `../../models/${name}.toml`,
        "ratings.duckdb",
        `splits/${split}.toml`,
      ],
    };

    runs[`run-${split}-default-${name}`] = {
      cmd: action_cmd(
        `movielens/${ds}`,
        "generate",
        "--default",
        `--split=splits/${split}.toml`,
        "--test-part=test",
        `-o runs/${split}-default/${name}`,
        name,
      ),
      outs: [`runs/${split}-default/${name}`],
      deps: [
        `../../models/${name}.toml`,
        "ratings.duckdb",
        `splits/${split}.toml`,
      ],
    };

    if (info.sweep == null) continue;

    runs[`run-${split}-sweep-best-${name}`] = {
      cmd: action_cmd(
        `movielens/${name}`,
        "generate",
        `--param-file=sweeps/${split}/${name}.json`,
        `--split=splits/${split}.toml`,
        "--test-part=test",
        `-o runs/${split}-sweep-best/${name}`,
        name,
      ),
      outs: [`runs/${split}-sweep-best/${name}`],
      deps: [
        `../../models/${name}.toml`,
        "ratings.duckdb",
        `splits/${split}.toml`,
        `sweeps/${split}/${name}.json`,
      ],
    };
  }

  return runs;
}
