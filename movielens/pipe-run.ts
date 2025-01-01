import { MODELS } from "../src/pipeline/model-config.ts";
import { Run } from "../src/pipeline/run.ts";

export function mlCrossfoldRuns(dataset: string, split: string): Run[] {
  const runs: Run[] = [];

  for (const [name, info] of Object.entries(MODELS)) {
    runs.push({
      name: `run-${split}-default-${name}`,
      dataset,
      args: ["--default"],
      model: name,
      split,
      variant: "default",
      deps: ["ratings.duckdb", `splits/${split}.duckdb`],
    });

    if (info.search?.grid) {
      runs.push({
        name: `run-${split}-grid-best-${name}`,
        dataset,
        args: [`--param-file=sweeps/${split}/${name}-grid.json`, "--test-part=-0"],
        model: name,
        split,
        variant: "grid-best",
        deps: ["ratings.duckdb", `splits/${split}.duckdb`, `sweeps/${split}/${name}-grid.json`],
      });
    }

    if (info.search?.params) {
      runs.push({
        name: `run-${split}-random-best-${name}`,
        dataset,
        args: [`--param-file=sweeps/${split}/${name}-random.json`, "--test-part=-0"],
        model: name,
        split,
        variant: "random-best",
        deps: ["ratings.duckdb", `splits/${split}.duckdb`, `sweeps/${split}/${name}-random.json`],
      });
    }
  }

  return runs;
}

export function mlSplitRuns(dataset: string, split: string): Run[] {
  const runs: Run[] = [];

  for (const [name, info] of Object.entries(MODELS)) {
    runs.push({
      name: `run-${split}-default-${name}`,
      dataset,
      args: ["--default"],
      model: name,
      split,
      variant: "default",
      deps: ["ratings.duckdb", `splits/${split}.toml`],
    });

    if (info.search?.grid) {
      runs.push({
        name: `run-${split}-grid-best-${name}`,
        dataset,
        args: [`--param-file=sweeps/${split}/${name}.json`, "--test-part=test"],
        model: name,
        split,
        variant: "grid-best",
        deps: ["ratings.duckdb", `splits/${split}.toml`, `sweeps/${split}/${name}-grid.json`],
      });
    }

    if (info.search?.params) {
      runs.push({
        name: `run-${split}-random-best-${name}`,
        dataset,
        args: [`--param-file=sweeps/${split}/${name}.json`, "--test-part=test"],
        model: name,
        split,
        variant: "random-best",
        deps: ["ratings.duckdb", `splits/${split}.toml`, `sweeps/${split}/${name}-random.json`],
      });
    }
  }

  return runs;
}

export function mlRuns(dataset: string, split: string, spec: { method: string }): Run[] {
  if (spec.method == "crossfold") {
    return mlCrossfoldRuns(dataset, split);
  } else {
    return mlSplitRuns(dataset, split);
  }
}
