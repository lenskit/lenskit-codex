import { expandGlob } from "std/fs/expand_glob.ts";
import { dirname, join as joinPath, normalize, parse as parsePath } from "std/path/mod.ts";
import { parse } from "std/yaml/mod.ts";

const ignores: Record<string, Set<string>> = {};

for await (let file of expandGlob("**/.gitignore", { exclude: [".pixi/**"] })) {
  await scanGitIgnore(file.path);
}

for await (let file of expandGlob("**/dvc.yaml", { exclude: [".pixi/**"] })) {
  await scanDvcYaml(file.path);
}

for (let [dir, ign] of Object.entries(ignores)) {
  let arr = Array.from(ign);
  arr.sort();
  let text = arr.map((l) => `${l}\n`).join("");
  console.log(text);
  let gifn = joinPath(dir, ".gitignore");
  await Deno.writeTextFile(gifn, text);
}

async function scanGitIgnore(path: string) {
  console.info("processing ignore file %s", path);
  let dir = dirname(path);
  let text = await Deno.readTextFile(path);
  let lines = text.split("\n");
  ignores[dir] = new Set(lines.map((l) => l.trim()).filter((l) => !l.match(/^\s*(#.*)?$/)));
}

async function scanDvcYaml(path: string) {
  console.info("processing DVC file %s", path);
  let text = await Deno.readTextFile(path);
  let data = parse(text);
  console.info(data);
  for (let [_name, stage] of Object.keys(data.stages)) {
    if (stage.outs) {
      for (let out of stage.outs) {
        if (typeof out == "string") {
          let dir = dirname(path);
          if (stage.wdir) {
            dir = joinPath(dir, stage.wdir);
          }
          let outPath = joinPath(dir, out);
          outPath = normalize(outPath);
          let p = parsePath(outPath);
          ignores[p.dir] ??= new Set();
          ignores[p.dir].add("/" + p.base);
        }
      }
    }
  }
}
