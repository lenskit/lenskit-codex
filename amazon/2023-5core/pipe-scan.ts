import { mapNotNullish } from "std/collections/mod.ts";
import { action_cmd } from "../../codex/dvc.ts";

import { sourceFiles } from "./pipe-sources.ts";

export const scanStages = {
  "scan-bench-users": {
    cmd: action_cmd(
      import.meta.url,
      "amazon collect-ids",
      "--user",
      "-D",
      "user-ids.duckdb",
      "data",
    ),
    deps: sourceFiles.map((s) => s.path),
    outs: ["user-ids.duckdb"],
  },
  "scan-bench-items": {
    cmd: action_cmd(
      import.meta.url,
      "amazon collect-ids",
      "--item",
      "-D",
      "item-ids.duckdb",
      "data",
    ),
    deps: sourceFiles.map((s) => s.path),
    outs: ["item-ids.duckdb"],
  },
  "convert-ratings": {
    foreach: sourceFiles.map((s) => `${s.cat}.${s.part}`),
    do: {
      cmd: action_cmd(
        import.meta.url,
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
    cmd: action_cmd(import.meta.url, "run-duck-sql", "--database=stats.duckdb", "bench-stats.sql"),
    outs: ["stats.duckdb"],
    deps: [
      "bench-stats.sql",
      ...sourceFiles.map((s) => s.path.replace(".csv.gz", ".parquet")),
    ],
  },
};
