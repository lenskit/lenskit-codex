import { join as joinPath, normalize, parse as parsePath, relative } from "std/path/mod.ts";
import { expandGlob } from "std/fs/mod.ts";

type Notebook = {
  dir: string;
  path: string;
  file: string;
  deps: string[];
};

async function collectNotebooks(): Promise<Notebook[]> {
  const notebooks: Notebook[] = [];
  for await (
    const nbf of expandGlob("**/*.qmd", { exclude: ["**/_*"], globstar: true })
  ) {
    let cwd = normalize(".");
    console.info("found notebook file %s", nbf.path);
    const path = parsePath(nbf.path);
    let dir = relative(cwd, path.dir);
    notebooks.push({
      dir,
      path: joinPath(dir, path.name),
      file: nbf.path,
      deps: [],
    });
  }
  return notebooks;
}

const notebooks = await collectNotebooks();

export const pipeline = {
  stages: {
    render: {
      foreach: notebooks.map((n) => n.path),
      do: {
        cmd: "quarto render ${item}.qmd",
        outs: ["_freeze/${item}"],
      },
    },
  },
};

export default pipeline;
