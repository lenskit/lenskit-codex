#! /usr/bin/env -S deno run --allow-read=. --allow-write=. --allow-net=deno.land
import { dirname, join as joinPath } from "std/path/mod.ts";
import * as yaml from "std/yaml/mod.ts";
import { expandGlob } from "std/fs/mod.ts";

for await (const pipe of expandGlob("**/pipeline.ts")) {
  console.info("rendering pipeline %s", pipe.path);
  const dir = dirname(pipe.path) ?? "";
  const mod = await import(pipe.path);
  let dvcfn = joinPath(dir, "dvc.yaml");
  console.info("writing DVC pipe %s", dvcfn);
  await Deno.writeTextFile(dvcfn, yaml.stringify(mod.pipeline));
  if (mod.subdirs) {
    for (const [n, p] of Object.entries(mod.subdirs)) {
      dvcfn = joinPath(dir, n, "dvc.yaml");
      console.info("writing DVC pipe %s", dvcfn);
      await Deno.writeTextFile(dvcfn, yaml.stringify(p));
    }
  }
}
