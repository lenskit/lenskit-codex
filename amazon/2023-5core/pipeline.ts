import { fromFileUrl } from "std/path/mod.ts";
import { expandGlob } from "std/fs/mod.ts";
import { action_cmd } from "../../codex/dvc.ts";

type SourceFile = {
  path: string;
  name: string;
  cat: string;
  part: string;
};

const sources: SourceFile[] = (await Array.fromAsync(
  expandGlob("data/*.csv.gz.dvc", { root: fromFileUrl(import.meta.resolve("./")) }),
)).map((e) => {
  const m = e.name.match(/^(?<name>(?<cat>.+)\.(?<part>\w+)\.csv\.gz)\.dvc/);
  if (!m) throw new Error(`invalid filename ${e.name}`);
  return {
    path: "data/" + m.groups!["name"],
    name: m.groups!["name"],
    cat: m.groups!["cat"],
    part: m.groups!["part"],
  };
});

export const pipeline = {
  stages: {
    "scan-bench-users": {
      cmd: action_cmd(
        import.meta.url,
        "amazon collect-ids",
        "--user",
        "-D",
        "user-ids.duckdb",
        "data",
      ),
      deps: sources.map((s) => s.path),
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
      deps: sources.map((s) => s.path),
      outs: ["item-ids.duckdb"],
    },
    "convert-ratings": {
      foreach: sources.map((s) => `${s.cat}.${s.part}`),
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
  },
};
