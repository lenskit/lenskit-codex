import { action_cmd } from "../../src/dvc.ts";

import { allSourceFiles } from "./pipe-sources.ts";

export const scanStages = {
  "scan-bench-users": {
    cmd: action_cmd(
      "amazon collect-ids",
      "--user",
      "-D",
      "user-ids.duckdb",
      "data",
    ),
    deps: allSourceFiles.map((s) => s.path),
    outs: ["user-ids.duckdb"],
  },
  "scan-bench-items": {
    cmd: action_cmd(
      "amazon collect-ids",
      "--item",
      "-D",
      "item-ids.duckdb",
      "data",
    ),
    deps: allSourceFiles.map((s) => s.path),
    outs: ["item-ids.duckdb"],
  },
  "convert-ratings": {
    foreach: allSourceFiles.map((s) => `${s.cat}.${s.part}`),
    do: {
      cmd: action_cmd(
        "amazon import-bench",
        "--users=user-ids.duckdb",
        "--items=item-ids.duckdb",
        "data/${item}.csv.gz",
      ),
      deps: [
        "user-ids.duckdb",
        "item-ids.duckdb",
        "data/${item}.csv.gz",
      ],
      outs: [
        "data/${item}.parquet",
      ],
    },
  },
  "collect-stats": {
    cmd: action_cmd("run-duck-sql", "-f bench-stats.sql", "stats.duckdb"),
    outs: ["stats.duckdb"],
    deps: [
      "bench-stats.sql",
      ...allSourceFiles.map((s) => s.path.replace(".csv.gz", ".parquet")),
    ],
  },
};
