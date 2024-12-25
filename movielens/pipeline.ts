import { parse as parsePath } from "std/path/mod.ts";
import { expandGlob } from "std/fs/mod.ts";
import * as toml from "std/toml/mod.ts";

import * as ai from "aitertools";

import { action_cmd, Pipeline, Stage } from "../src/dvc.ts";

import { mlCrossfoldRuns, mlSplitRuns } from "./pipe-run.ts";
import { mlSweep } from "./pipe-sweep.ts";

type SplitSpec = {
  source: string;
  method: string;
};

const datasets: Record<string, string> = {
  ML100K: "ml-100k",
  ML1M: "ml-1m",
  ML10M: "ml-10m",
  ML20M: "ml-20m",
  ML25M: "ml-25m",
  ML32M: "ml-32m",
};

async function scanSplits(name: string): Promise<Record<string, SplitSpec>> {
  let splits: Record<string, SplitSpec> = {};
  for await (const file of expandGlob(`movielens/${name}/splits/*.toml`)) {
    const spec = toml.parse(await Deno.readTextFile(file.path));
    const path = parsePath(file.path);
    splits[path.name] = spec as SplitSpec;
  }
  return splits;
}

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

function mlSplit(
  name: string,
  split: string,
  spec: SplitSpec,
): Record<string, Stage> {
  if (spec.method == "crossfold") {
    return {
      [`split-${split}`]: {
        cmd: action_cmd(`movielens/${name}/splits`, "split", `${split}.toml`),
        wdir: "splits",
        params: [{ "../../../config.toml": ["random.seed"] }],
        deps: [`${split}.toml`, spec.source as string],
        outs: [`${split}.duckdb`],
      },
    };
  } else {
    return {};
  }
}

async function ml_pipeline(name: string): Promise<Pipeline> {
  const fn = datasets[name];

  let splits = await scanSplits(name);

  let split_stages: Record<string, Stage> = {};
  let sweep_stages: Record<string, Stage> = {};
  let run_stages: Record<string, Stage> = {};
  for (let [split, spec] of Object.entries(splits)) {
    Object.assign(split_stages, mlSplit(name, split, spec));
    Object.assign(sweep_stages, mlSweep(name, split));
    if (spec.method == "crossfold") {
      Object.assign(run_stages, mlCrossfoldRuns(name, split));
    } else {
      Object.assign(run_stages, mlSplitRuns(name, split));
    }
  }

  return {
    stages: {
      import: ml_import(name, fn),

      ...split_stages,
      ...sweep_stages,
      ...run_stages,

      "collect-metrics": {
        cmd: action_cmd(
          `movielens/${name}`,
          "collect metrics",
          "run-metrics.duckdb",
          "--view-script=../ml-run-metrics.sql",
          "runs",
        ),
        // @ts-ignore i'm lazy
        deps: Object.values(run_stages).map((s) => s.outs).flat().filter((d) =>
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
