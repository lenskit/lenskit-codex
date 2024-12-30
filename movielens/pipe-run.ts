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

    if (info.sweep == null) continue;

    runs.push({
      name: `run-${split}-sweep-best-${name}`,
      dataset,
      args: [`--param-file=sweeps/${split}/${name}.json`, "--test-part=-0"],
      model: name,
      split,
      variant: "sweep-best",
      deps: ["ratings.duckdb", `splits/${split}.duckdb`, `sweeps/${split}/${name}.json`],
    });
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

    if (info.sweep == null) continue;

    runs.push({
      name: `run-${split}-sweep-best-${name}`,
      dataset,
      args: [`--param-file=sweeps/${split}/${name}.json`, "--test-part=-0"],
      model: name,
      split,
      variant: "sweep-best",
      deps: ["ratings.duckdb", `splits/${split}.toml`, `sweeps/${split}/${name}.json`],
    });
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
