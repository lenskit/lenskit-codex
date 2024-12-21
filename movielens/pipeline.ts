import { parse as parsePath } from "std/path/mod.ts";
import { expandGlob } from "std/fs/mod.ts";
import * as toml from "std/toml/mod.ts";
import { filterValues } from "std/collections/mod.ts";

import * as ai from "aitertools";

import { action_cmd, Pipeline, Stage } from "../src/dvc.ts";
import { MODELS } from "../src/pipeline/model-config.ts";

export const datasets: Record<string, string> = {
  ML100K: "ml-100k",
  ML1M: "ml-1m",
  ML10M: "ml-10m",
  ML20M: "ml-20m",
  ML25M: "ml-25m",
  ML32M: "ml-32m",
};

function ml_import(name: string, fn: string): Stage {
  return {
    cmd: action_cmd(
      `movielens/${name}`,
      "movielens import",
      "--stat-sql=../ml-stats.sql",
      `${fn}.zip`,
    ),
    deps: ["../ml-stats.sql", fn + ".zip"],
    outs: ["ratings.duckdb"],
  };
}

async function ml_splits(name: string): Promise<Record<string, Stage>> {
  const stages: Record<string, Stage> = {};
  for await (const file of expandGlob(`movielens/${name}/splits/*.toml`)) {
    const path = parsePath(file.path);
    const split = toml.parse(await Deno.readTextFile(file.path));
    stages[`split-${path.name}`] = {
      cmd: action_cmd(`movielens/${name}/splits`, "split", path.base),
      wdir: "splits",
      params: [{ "../../../config.toml": ["random.seed"] }],
      deps: [path.base, split.source as string],
      outs: [`${path.name}.duckdb`],
    };
  }
  return stages;
}

function ml_sweeps(ds: string): Record<string, Stage> {
  const active = filterValues(MODELS, (m) => m.sweep != null);
  const results: Record<string, Stage> = {};
  for (const [name, info] of Object.entries(active)) {
    results[`sweep-random-${name}`] = {
      cmd: action_cmd(
        `movielens/${ds}`,
        "sweep run",
        "-p 0",
        "--ratings=ratings.duckdb",
        "--assignments=splits/random.duckdb",
        name,
        `sweeps/random/${name}.duckdb`,
      ),
      params: [{ "../../config.toml": ["random.seed"] }],
      deps: [
        "splits/random.duckdb",
        "ratings.duckdb",
        `../../codex/models/${name.replaceAll("-", "_")}.py`,
      ],
      outs: [`sweeps/random/${name}.duckdb`],
    };
    const metric = info.predictor ? "rmse" : "ndcg";
    results[`export-random-${name}`] = {
      cmd: action_cmd(`movielens/${ds}`, "sweep export", `sweeps/random/${name}.duckdb`, metric),
      deps: [`sweeps/random/${name}.duckdb`],
      outs: [
        `sweeps/random/${name}.csv`,
        { [`sweeps/random/${name}.json`]: { cache: false } },
      ],
    };
  }

  return results;
}

function ml_runs(ds: string): Record<string, Stage> {
  const runs: Record<string, Stage> = {};

  for (const [name, info] of Object.entries(MODELS)) {
    runs[`run-random-default-${name}`] = {
      cmd: action_cmd(
        `movielens/${ds}`,
        "generate",
        "--default",
        "--test-part=-0",
        "--assignments=splits/random.duckdb",
        "--ratings=ratings.duckdb",
        `-o runs/random-default/${name}`,
        name,
      ),
      outs: [`runs/random-default/${name}`],
      deps: [
        `../../codex/models/${name.replaceAll("-", "_")}.py`,
        "ratings.duckdb",
        "splits/random.duckdb",
      ],
    };

    if (info.sweep == null) continue;

    runs[`run-random-sweep-best-${name}`] = {
      cmd: action_cmd(
        `movielens/${name}`,
        "generate",
        `--param-file=sweeps/random/${name}.json`,
        "--test-part=-0",
        "--assignments=splits/random.duckdb",
        "--ratings=ratings.duckdb",
        `-o runs/random-sweep-best/${name}.duckdb`,
        name,
      ),
      outs: [`runs/random-sweep-best/${name}.duckdb`],
      deps: [
        `../../codex/models/${name.replaceAll("-", "_")}.py`,
        "ratings.duckdb",
        "splits/random.duckdb",
        `sweeps/random/${name}.json`,
      ],
    };
  }

  return runs;
}

async function ml_pipeline(name: string): Promise<Pipeline> {
  const fn = datasets[name];
  let splits = await ml_splits(name);
  let sweeps = ml_sweeps(name);
  let runs = ml_runs(name);

  return {
    stages: {
      import: ml_import(name, fn),

      ...splits,
      ...sweeps,
      ...runs,

      "collect-metrics": {
        cmd: action_cmd(
          `movielens/${name}`,
          "collect metrics",
          "run-metrics.duckdb",
          "--view-script=../ml-run-metrics.sql",
          "runs",
        ),
        // @ts-ignore i'm lazy
        deps: Object.values(runs).map((s) => s.outs).flat().filter((d) =>
          typeof d == "string" && d.endsWith(".duckdb")
        ),
        outs: ["run-metrics.duckdb"],
      },
    },
  };
}

export const pipeline: Pipeline = {
  stages: {
    aggregate: {
      cmd: action_cmd(
        import.meta.url,
        "movielens aggregate",
        "-d merged-stats.duckdb",
        ...Object.keys(datasets),
      ),
      deps: Object.keys(datasets).map((n) => `${n}/ratings.duckdb`),
      outs: ["merged-stats.duckdb"],
    },
  },
};

export const subdirs = await ai.toMap(
  ai.map(
    async (name: string) => [name, await ml_pipeline(name)],
    ai.fromIterable(Object.keys(datasets)),
  ),
);
