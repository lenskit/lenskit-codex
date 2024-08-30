/**
 * Model run stages for the Amazon pipeline.
 */
import { action_cmd, generateStages, Stage } from "../../codex/dvc.ts";
import { MODELS } from "../../codex/models/model-list.ts";

import { categories } from "./pipe-sources.ts";

function defaultRunStage(
  name: string,
  test: "test" | "valid",
): Stage {
  let trainFiles = ["data/${item}.train.parquet"];
  let testFile = "data/${item}.valid.parquet";
  if (test == "test") {
    trainFiles.push(testFile);
    testFile = "data/${item}.test.parquet";
  }

  return {
    foreach: categories,
    do: {
      cmd: action_cmd(
        import.meta.url,
        "generate",
        "--default",
        "-n 2000",
        ...trainFiles.map((f) => `--train=${f}`),
        `--test=${testFile}`,
        `-o runs/default/\${item}/${test}/${name}.duckdb`,
        name,
      ),
      deps: [
        ...trainFiles,
        testFile,
      ],
      outs: [`runs/default/\${item}/${test}/${name}.duckdb`],
    },
  };
}

function sweepStage(name: string) {
  let trainFile = "data/${item}.train.parquet";
  let testFile = "data/${item}.valid.parquet";
  let outFile = `sweeps/\${item}/${name}.duckdb`;

  return {
    foreach: categories,
    do: {
      cmd: action_cmd(
        import.meta.url,
        "sweep",
        "-n 1000",
        `--train=${trainFile}`,
        `--test=${testFile}`,
        `-o ${outFile}`,
        name,
      ),
      deps: [
        trainFile,
        testFile,
      ],
      outs: [outFile],
    },
  };
}

export const runStages: Record<string, Stage> = generateStages(
  Object.entries(MODELS),
  ([name, info]) => {
    let result: Record<string, Stage> = {
      [`run-default-${name}-test`]: defaultRunStage(name, "test"),
      [`run-default-${name}-valid`]: defaultRunStage(name, "valid"),
    };
    if (info.sweepable) {
      result[`sweep-${name}`] = sweepStage(name);
    }
    return result;
  },
);
