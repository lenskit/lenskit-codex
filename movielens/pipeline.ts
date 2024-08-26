import { parse as parsePath } from "std/path/mod.ts";
import { expandGlob } from "std/fs/mod.ts";
import * as toml from "std/toml/mod.ts";
import { filterValues, mapEntries, mapValues } from "std/collections/mod.ts";

import * as ai from "aitertools";

import { Pipeline, Stage } from "../codex/dvc.ts";
import { MODELS } from "../codex/models/model-list.ts";

export const datasets: Record<string, string> = {
  ML100K: "ml-100k",
  ML1M: "ml-1m",
  ML10M: "ml-10m",
  ML20M: "ml-20m",
  ML25M: "ml-25m",
  ML32M: "ml-32m",
};

function ml_import(_name: string, fn: string): Stage {
  return {
    cmd: `python ../import-ml.py ${fn}.zip`,
    deps: ["../import-ml.py", "../ml-stats.sql", fn + ".zip"],
    outs: ["ratings.duckdb"],
  };
}

async function ml_splits(name: string): Promise<Record<string, Stage>> {
  const stages: Record<string, Stage> = {};
  for await (const file of expandGlob(`movielens/${name}/splits/*.toml`)) {
    const path = parsePath(file.path);
    const split = toml.parse(await Deno.readTextFile(file.path));
    stages[`split-${path.name}`] = {
      cmd: `python ../../../scripts/split.py ${path.base}`,
      wdir: "splits",
      params: [{ "../../../config.toml": ["random.seed"] }],
      deps: [path.base, split.source as string],
      outs: [`${path.name}.duckdb`],
    };
  }
  return stages;
}

function ml_sweeps(_name: string): Record<string, Stage> {
  const active = filterValues(MODELS, (m) => m.sweepable);
  const results: Record<string, Stage> = {};
  for (const [name, info] of Object.entries(active)) {
    results[`sweep-random-${name}`] = {
      cmd:
        `python ../../scripts/sweep.py -p 1 ${name} splits/random.duckdb ratings.duckdb sweeps/random/${name}.duckdb`,
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
      cmd: `python ../../scripts/sweep.py --export sweeps/random/${name}.duckdb ${metric}`,
      deps: ["../../scripts/sweep.py", `sweeps/random/${name}.duckdb`],
      outs: [
        `sweeps/random/${name}.csv`,
        { [`sweeps/random/${name}.json`]: { cache: false } },
      ],
    };
  }

  return results;
}

function ml_runs(_name: string): Record<string, Stage> {
  const runs: Record<string, Stage> = {};

  for (const [name, info] of Object.entries(MODELS)) {
    let outs: Record<string, string> = {
      stats: `runs/random-default/${name}.json`,
      recommendations: `runs/random-default/${name}-recs.parquet`,
    };
    if (info.predictor) {
      outs["predictions"] = `runs/random-default/${name}-preds.parquet`;
    }
    let out_flags = Object.entries(outs).map(([k, f]) => `--${k}=${f}`).join(" ");
    runs[`run-random-default-${name}`] = {
      cmd:
        `python ../../scripts/generate.py --default ${out_flags} --ratings ratings.duckdb --test-part 2-5 ${name} splits/random.duckdb`,
      outs: Object.values(outs),
      deps: [
        "../../scripts/generate.py",
        `../../codex/models/${name.replaceAll("-", "_")}.py`,
        "ratings.duckdb",
        "splits/random.duckdb",
      ],
    };

    if (!info.sweepable) continue;

    outs = mapValues(outs, (v) => v.replace("default", "sweep-best"));
    out_flags = Object.entries(outs).map(([k, f]) => `--${k}=${f}`).join(" ");
    runs[`run-random-sweep-best-${name}`] = {
      cmd:
        `python ../../scripts/generate.py --param-file=sweeps/random/${name}.json ${out_flags} --ratings ratings.duckdb --test-part 2-5 ${name} splits/random.duckdb`,
      outs: Object.values(outs),
      deps: [
        "../../scripts/generate.py",
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
  return {
    stages: Object.assign(
      {
        ["import"]: ml_import(name, fn),
      },
      await ml_splits(name),
      ml_sweeps(name),
      ml_runs(name),
    ),
  };
}

export const pipeline: Pipeline = {
  stages: {
    aggregate: {
      cmd: "python aggregate-ml.py -d merged-stats.duckdb " + Object.keys(datasets).join(" "),
      deps: ["aggregate-ml.py"].concat(Object.keys(datasets).map((n) => `${n}/ratings.duckdb`)),
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
