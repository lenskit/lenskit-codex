import { fromFileUrl } from "std/path/mod.ts";
import { expandGlob } from "std/fs/mod.ts";
import { mapNotNullish } from "std/collections/mod.ts";

export type SourceFile = {
  path: string;
  name: string;
  cat: string;
  part: string;
};

export const sourceFiles: SourceFile[] = (await Array.fromAsync(
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

export const categories: string[] = mapNotNullish(
  sourceFiles,
  (s) => (s.part == "train" ? s.cat : undefined),
);
