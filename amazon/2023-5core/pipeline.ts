import { fromFileUrl } from "std/path/mod.ts";
import { expandGlob, WalkEntry } from "std/fs/mod.ts";
import * as ai from "aitertools";

const datasets = await ai.toArray(ai.map((e: WalkEntry) => {
  return e.name.replace(/\.train.*/, "");
}, expandGlob("data/*.train.csv.gz", { root: fromFileUrl(import.meta.resolve("./")) })));

export const pipeline = {
  stages: {
    "import-bench": {
      foreach: datasets,
      do: {
        cmd: "python ../import-az.py --benchmark --stat-script az-bench-stats.sql data/${item}",
        deps: [
          "../import-az.py",
          "../schemas/benchmark.sql",
          "az-bench-stats.sql",
          "data/${item}.train.csv.gz",
          "data/${item}.valid.csv.gz",
          "data/${item}.test.csv.gz",
        ],
        outs: [
          "data/${item}.duckdb",
        ],
      },
    },
  },
};
