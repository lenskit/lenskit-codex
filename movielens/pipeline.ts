import { parse as parsePath } from "std/path/mod.ts";
import { expandGlob } from "std/fs/mod.ts";
import * as toml from "std/toml/mod.ts";

import * as ai from "aitertools";

import { Pipeline, Stage } from "../codex/dvc.ts";

export const datasets: Record<string, string> = {
  ML100K: "ml-100k",
  ML1M: "ml-1m",
  ML10M: "ml-10m",
  ML20M: "ml-20m",
  ML25M: "ml-25m",
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

async function ml_pipeline(name: string): Promise<Pipeline> {
  const fn = datasets[name];
  return {
    stages: Object.assign({
      ["import-" + fn]: ml_import(name, fn),
    }, await ml_splits(name)),
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
