/**
 * Model run stages for the Amazon pipeline.
 */
import { mapEntries } from "std/collections/mod.ts";
import { action_cmd, Stage } from "../../codex/dvc.ts";
import { MODELS } from "../../codex/models/model-list.ts";

import { categories } from "./pipe-sources.ts";
import { ModelInfo } from "../../codex/models/model-list.ts";

function defaultRunStage(
  [name, _info]: [string, ModelInfo],
  test: "test" | "valid",
): [string, Stage] {
  let trainFiles = ["data/${item}.train.parquet"];
  let testFile = "data/${item}.valid.parquet";
  if (test == "test") {
    trainFiles.push(testFile);
    testFile = "data/${item}.test.parquet";
  }

  return [
    `run-default-${name}-${test}`,
    {
      foreach: categories,
      do: {
        cmd: action_cmd(
          import.meta.url,
          "generate",
          "--default",
          "-n 2000",
          ...trainFiles.map((f) => `--train=${f}`),
          `--test=${testFile}`,
          `-o runs/default/\${item}/${name}.duckdb`,
          name,
        ),
        deps: [
          ...trainFiles,
          testFile,
        ],
        outs: [`runs/default/\${item}/${test}/${name}.duckdb`],
      },
    },
  ];
}

export const runStages = {
  ...mapEntries(MODELS, (m) => defaultRunStage(m, "test")),
  ...mapEntries(MODELS, (m) => defaultRunStage(m, "valid")),
};
