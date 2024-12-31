/**
 * Model run stages for the Amazon pipeline.
 */
import { action_cmd, generateStages, Stage } from "../../src/dvc.ts";
import { MODELS } from "../../src/pipeline/model-config.ts";

import { categories } from "./pipe-sources.ts";

function runStage(
  name: string,
  test: "test" | "valid",
  config: "default" | "grid-best" = "default",
): Stage {
  let depFiles = ["data/${item}.train.parquet", "data/${item}.valid.parquet"];
  if (test == "test") {
    depFiles.push("data/${item}.test.parquet");
  }

  let cfgArgs = [];
  let cfgDeps = [];
  if (config == "default") {
    cfgArgs = ["--default"];
  } else if (config == "grid-best") {
    let f = `sweeps/\${item}/${name}.json`;
    cfgArgs = ["--param-file", f];
    cfgDeps.push(f);
  } else {
    throw new Error("invalid configuration");
  }

  return {
    foreach: categories,
    do: {
      cmd: action_cmd(
        "generate",
        ...cfgArgs,
        "-n 2000",
        "--split=data/${item}",
        `--test-part=${test}`,
        `-o runs/${config}/\${item}/${test}/${name}`,
        name,
      ),
      deps: [
        ...cfgDeps,
        ...depFiles,
      ],
      outs: [`runs/${config}/\${item}/${test}/${name}`],
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
        "sweep run",
        "-n 1000",
        `--train=${trainFile}`,
        `--test=${testFile}`,
        name,
        outFile,
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
      [`run-default-${name}-test`]: runStage(name, "test"),
      [`run-default-${name}-valid`]: runStage(name, "valid"),
    };
    if (info.grid) {
      let sweepDb = `sweeps/\${item}/${name}.duckdb`;
      result[`sweep-${name}`] = sweepStage(name);
      result[`export-sweep-${name}`] = {
        foreach: categories,
        do: {
          cmd: action_cmd(
            "sweep export",
            sweepDb,
            info.predictor ? "rmse" : "ndcg",
          ),
          deps: [
            sweepDb,
          ],
          outs: [
            sweepDb.replace(/\.duckdb$/, ".csv"),
            { [sweepDb.replace(/\.duckdb$/, ".json")]: { cache: false } },
          ],
        },
      };
      result[`run-grid-best-${name}-test`] = runStage(
        name,
        "test",
        "grid-best",
      );
    }
    return result;
  },
);
