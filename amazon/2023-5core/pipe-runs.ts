/**
 * Model run stages for the Amazon pipeline.
 */
import { mapEntries } from "std/collections/mod.ts";
import { action_cmd, Stage } from "../../codex/dvc.ts";
import { MODELS } from "../../codex/models/model-list.ts";

import { categories } from "./pipe-sources.ts";
import { ModelInfo } from "../../codex/models/model-list.ts";

function defaultRunStage([name, _info]: [string, ModelInfo]): [string, Stage] {
  return [
    `run-default-${name}-test`,
    {
      foreach: categories,
      do: {
        cmd: action_cmd(
          import.meta.url,
          "generate",
          "--default",
          "-n 2000",
          "--train=data/${item}.train.parquet",
          "--train=data/${item}.valid.parquet",
          "--test=data/${item}.test.parquet",
          `-o runs/default/\${item}/${name}.duckdb`,
          name,
        ),
        deps: [
          "data/${item}.train.parquet",
          "data/${item}.valid.parquet",
          "data/${item}.test.parquet",
        ],
        outs: [`runs/default/\${item}/${name}.duckdb`],
      },
    },
  ];
}

export const runStages = {
  ...mapEntries(MODELS, defaultRunStage),
};
