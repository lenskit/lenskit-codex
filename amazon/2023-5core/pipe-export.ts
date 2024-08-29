import { mapNotNullish } from "std/collections/mod.ts";
import { assert } from "std/assert/mod.ts";
import { basename } from "std/path/mod.ts";

import { action_cmd, isSingleStage } from "../../codex/dvc.ts";
import { categories, sourceFiles } from "./pipe-sources.ts";
import { runStages } from "./pipe-runs.ts";
import { map } from "aitertools";
import { MODELS } from "../../codex/models/model-list.ts";
export { runStages } from "./pipe-runs.ts";

function* exportableRuns(models: [string, unknown][], categories: string[]) {
  for (let cat of categories) {
    for (let [model, _info] of models) {
      yield {
        model,
        config: "default",
        cat,
        part: "valid",
      };
      yield {
        model,
        config: "default",
        cat,
        part: "test",
      };
    }
  }
}

export const exportStages = {
  "export-qrels": {
    foreach: mapNotNullish(sourceFiles, (s) => s.part == "test" ? s.base : null),
    do: {
      cmd: action_cmd(
        import.meta.url,
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
        import.meta.url,
        "trec export runs",
        "runs/${item.config}/${item.cat}/${item.part}/${item.model}.duckdb",
        "runs/${item.config}/${item.cat}/${item.part}/${item.model}.run.gz",
      ),
      deps: ["runs/${item.config}/${item.cat}/${item.part}/${item.model}.duckdb"],
      outs: ["runs/${item.config}/${item.cat}/${item.part}/${item.model}.run.gz"],
    },
  },
};
