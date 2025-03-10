import { join as joinPath, normalize, parse as parsePath, relative } from "@std/path";
import { expandGlob } from "@std/fs";
import { extract } from "@std/front-matter/yaml";

import { Pipeline } from "./src/dvc.ts";

type Notebook = {
  dir: string;
  path: string;
  file: string;
  deps: string[];
  outs?: string[];
};

async function collectNotebooks(): Promise<Notebook[]> {
  const notebooks: Notebook[] = [];
  for await (
    const nbf of expandGlob("**/*.qmd", { exclude: [".pixi/**", "**/_*"], globstar: true })
  ) {
    const cwd = normalize(".");
    console.info("found notebook file %s", nbf.path);
    const path = parsePath(nbf.path);
    const dir = relative(cwd, path.dir);
    const text = await Deno.readTextFile(nbf.path);
    // deno-lint-ignore no-explicit-any
    const parsed: any = extract(text);
    let deps: string[];
    if (typeof parsed.attrs.deps == "string") {
      deps = [parsed.attrs.deps];
    } else {
      deps = (parsed.attrs.deps as string[]) ?? [];
    }
    deps = deps.map((p) => relative(cwd, normalize(joinPath(dir, p))));
    let outs = undefined;
    if (parsed.attrs.outs) {
      outs = parsed.attrs.outs as string[];
      outs = outs.map((p) => relative(cwd, normalize(joinPath(dir, p))));
    }
    notebooks.push({
      dir,
      path: joinPath(dir, path.name),
      file: joinPath(dir, nbf.name),
      deps,
      outs,
    });
  }
  return notebooks;
}

export const pipeline: Pipeline = {
  stages: {},
};

for (const nb of await collectNotebooks()) {
  pipeline.stages[`page/${nb.path}`] = {
    cmd: `quarto render ${nb.file} --profile prerender`,
    deps: ["_quarto-prerender.yml", "_quarto.yml", nb.file].concat(nb.deps),
    outs: [`_freeze/${nb.path}`].concat(nb.outs ?? []),
  };
}

export default pipeline;
