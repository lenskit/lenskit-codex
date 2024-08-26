#! /usr/bin/env -S deno run --allow-read=. --allow-write=. --allow-net=deno.land
import { dirname, join as joinPath } from "std/path/mod.ts";
import * as toml from "std/toml/mod.ts";
import { expandGlob } from "std/fs/mod.ts";
import * as z from "zod";

const COPYDOC_SCHEMA = z.object({
  source: z.string(),
  replacements: z.array(z.object({
    match: z.string(),
    replace: z.string(),
    regex: z.boolean().default(false),
  })),
  documents: z.record(
    z.string(),
    z.object({}),
  ).transform((r) => new Map(Object.entries(r))),
});

for await (const copy of expandGlob("**/copydoc.toml", { exclude: [".*"] })) {
  const tgt_dir = dirname(copy.path);
  console.info("processing copies for %s", tgt_dir);
  const spec = COPYDOC_SCHEMA.parse(toml.parse(await Deno.readTextFile(copy.path)));
  const src_dir = joinPath(tgt_dir, spec.source);

  for (const name of spec.documents.keys()) {
    const src_fn = joinPath(src_dir, `${name}.qmd`);
    console.info("%s: copying %s", tgt_dir, src_fn);
    let text = await Deno.readTextFile(src_fn);
    for (const repl of spec.replacements) {
      text = text.replaceAll(repl.match, repl.replace);
    }
    await Deno.writeTextFile(joinPath(tgt_dir, `${name}.qmd`), text);
  }
}
