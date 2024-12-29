import { mapNotNullish } from "std/collections/mod.ts";

import { action_cmd } from "../../src/dvc.ts";
import { categories, sourceFiles } from "./pipe-sources.ts";
import { MODELS } from "../../src/pipeline/model-config.ts";

function* exportableRuns(models: [string, unknown][], categories: string[]) {
  for (let cat of categories) {
    for (let [model, _info] of models) {
      yield `runs/default/${cat}/valid/${model}`;
      yield `runs/default/${cat}/test/${model}`;
    }
  }
}

export const exportStages = {
  "export-qrels": {
    foreach: mapNotNullish(
      sourceFiles,
      (s) => (s.part == "test" || s.part == "valid") ? s.base : null,
    ),
    do: {
      cmd: action_cmd(
        "trec export qrels",
        "data/${item}.parquet",
      ),
      deps: [
        "data/${item}.parquet",
      ],
      outs: [
        "data/${item}.qrels.gz",
      ],
    },
  },
  "export-default-runs": {
    foreach: Array.from(exportableRuns(Object.entries(MODELS), categories)),
    do: {
      cmd: action_cmd(
        "trec export runs",
        "${item}.duckdb",
        "${item}.run.gz",
      ),
      deps: ["${item}.duckdb"],
      outs: ["${item}.run.gz"],
    },
  },
};
