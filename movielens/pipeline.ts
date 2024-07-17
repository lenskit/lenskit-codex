import { Pipeline, Stage } from "../codex/dvc.ts";

export const datasets: Record<string, string> = {
  ML100K: "ml-100k",
  ML1M: "ml-1m",
  ML10M: "ml-10m",
  ML20M: "ml-20m",
  ML25M: "ml-25m",
};

function ml_import(name: string, file: string): Stage {
  return {
    cmd: `python ../import-ml.py ${file}.zip`,
    deps: ["../import-ml.py", file + ".zip"],
    outs: ["ratings.parquet"],
  };
}

function ml_stats(name: string): Stage {
  return {
    cmd: "python ../../scripts/duckdb-sql.py -d stats.duckdb ../ml-stats.sql",
    deps: [
      "../ml-stats.sql",
      "ratings.parquet",
    ],
    outs: [
      "stats.duckdb",
    ],
  };
}

function ml_pipeline(name: string): Pipeline {
  let fn = datasets[name];
  return {
    stages: {
      ["import-" + fn]: ml_import(name, fn),
      [fn + "-stats"]: ml_stats(name),
    },
  };
}

export const pipeline: Pipeline = {
  stages: {
    aggregate: {
      cmd: "python aggregate-ml.py -d merged-stats.duckdb" + Object.keys(datasets).join(" "),
      deps: ["aggregate-ml.py"].concat(Object.keys(datasets).map((n) => `${n}/stats.duckdb`)),
      outs: ["merged-stats.duckdb"],
    },
  },
};

export const subdirs = Object.fromEntries(Object.keys(datasets).map((n) => [n, ml_pipeline(n)]));
