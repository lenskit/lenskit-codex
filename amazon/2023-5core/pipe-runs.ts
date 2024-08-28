/**
 * Model run stages for the Amazon pipeline.
 */
import { mapEntries } from "std/collections/mod.ts";
import { action_cmd, Stage } from "../../codex/dvc.ts";
import { MODELS } from "../../codex/models/model-list.ts";

import { categories } from "./pipe-sources.ts";
import { ModelInfo } from "../../codex/models/model-list.ts";

function defaultRunStage([name, info]: [string, ModelInfo]): [string, Stage] {
  const outs: Record<string, string> = {
    stats: `runs/default/\${item}/${name}.json`,
    recommendations: `runs/default/\${item}/${name}-recs.parquet`,
  };
  if (info.predictor) {
    outs["predictions"] = `runs/default/\${item}/${name}-preds.parquet`;
  }
  return [
    `run-default-${name}-test`,
    {
      foreach: categories,
      do: {
        cmd: action_cmd(
          import.meta.url,
          "generate",
          "--default",
          "--train=data/${item}.train.parquet",
          "--train=data/${item}.valid.parquet",
          "--test=data/${item}.test.parquet",
          ...Object.entries(outs).map(([k, f]) => `--${k}=${f}`),
          name,
        ),
        deps: [
          "data/${item}.train.parquet",
          "data/${item}.valid.parquet",
          "data/${item}.test.parquet",
        ],
        outs: Object.values(outs),
      },
    },
  ];
}

export const runStages = {
  ...mapEntries(MODELS, defaultRunStage),
};
