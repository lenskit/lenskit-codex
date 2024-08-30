/**
 * Model run stages for the Amazon pipeline.
 */
import { action_cmd, generateStages, Stage } from "../../codex/dvc.ts";
import { MODELS } from "../../codex/models/model-list.ts";

import { categories } from "./pipe-sources.ts";

function runStage(
  name: string,
  test: "test" | "valid",
  config: "default" | "sweep-best" = "default",
): Stage {
  let trainFiles = ["data/${item}.train.parquet"];
  let testFile = "data/${item}.valid.parquet";
  if (test == "test") {
    trainFiles.push(testFile);
    testFile = "data/${item}.test.parquet";
  }

  let cfgArgs = [];
  let cfgDeps = [];
  if (config == "default") {
    cfgArgs = ["--default"];
  } else if (config == "sweep-best") {
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
        import.meta.url,
        "generate",
        ...cfgArgs,
        "-n 2000",
        ...trainFiles.map((f) => `--train=${f}`),
        `--test=${testFile}`,
        `-o runs/${config}/\${item}/${test}/${name}.duckdb`,
        name,
      ),
      deps: [
        ...cfgDeps,
        ...trainFiles,
        testFile,
      ],
      outs: [`runs/${config}/\${item}/${test}/${name}.duckdb`],
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
    if (info.sweepable) {
      let sweepDb = `sweeps/\${item}/${name}.duckdb`;
      result[`sweep-${name}`] = sweepStage(name);
      result[`export-sweep-${name}`] = {
        foreach: categories,
        do: {
          cmd: action_cmd(
            import.meta.url,
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
      result[`run-sweep-best-${name}-test`] = runStage(
        name,
        "test",
        "sweep-best",
      );
    }
    return result;
  },
);
