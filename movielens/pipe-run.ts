import { MODELS } from "../src/pipeline/model-config.ts";
import { Run } from "../src/pipeline/run.ts";

export function mlCrossfoldRuns(split: string): Run[] {
  const runs: Run[] = [];

  for (const [name, info] of Object.entries(MODELS)) {
    runs.push({
      name: `run-${split}-default-${name}`,
      args: ["--default"],
      model: name,
      split,
      variant: "default",
      deps: ["ratings.duckdb", `splits/${split}.duckdb`],
    });

    if (info.sweep == null) continue;

    runs.push({
      name: `run-${split}-default-${name}`,
      args: [`--param-file=sweeps/${split}/${name}.json`, "--test-part=-0"],
      model: name,
      split,
      variant: "sweep-best",
      deps: ["ratings.duckdb", `splits/${split}.duckdb`, `sweeps/${split}/${name}.json`],
    });
  }

  return runs;
}

export function mlSplitRuns(split: string): Run[] {
  const runs: Run[] = [];

  for (const [name, info] of Object.entries(MODELS)) {
    runs.push({
      name: `run-${split}-default-${name}`,
      args: ["--default"],
      model: name,
      split,
      variant: "default",
      deps: ["ratings.duckdb", `splits/${split}.toml`],
    });

    if (info.sweep == null) continue;

    runs.push({
      name: `run-${split}-default-${name}`,
      args: [`--param-file=sweeps/${split}/${name}.json`, "--test-part=-0"],
      model: name,
      split,
      variant: "sweep-best",
      deps: ["ratings.duckdb", `splits/${split}.toml`, `sweeps/${split}/${name}.json`],
    });
  }

  return runs;
}

export function mlRuns(split: string, spec: { method: string }): Run[] {
  if (spec.method == "crossfold") {
    return mlCrossfoldRuns(split);
  } else {
    return mlSplitRuns(split);
  }
}
