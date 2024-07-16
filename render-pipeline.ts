#! /usr/bin/env -S deno run --allow-read=. --allow-write=. --allow-net=deno.land
import { join as joinPath } from "std/path/mod.ts";
import * as yaml from "std/yaml/mod.ts";
import { expandGlob } from "std/fs/mod.ts";

for await (const pipe of expandGlob("**/pipeline.ts")) {
  console.info("rendering pipeline %s", pipe.path);
  const mod = await import(pipe.path);
  console.log("pipeline: %o", mod.default);
  await Deno.writeTextFile(joinPath(mod.dir ?? "", "dvc.yaml"), yaml.stringify(mod.default));
}
