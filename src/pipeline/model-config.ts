import { sortBy } from "std/collections/mod.ts";
import { fromFileUrl, join, parse } from "std/path/mod.ts";
import { parse as parseToml } from "std/toml/mod.ts";

import * as z from "zod";

export const MODEL_CONFIG_SCHEMA = z.object({
  scorer: z.string(),
  enabled: z.boolean().default(true),
  predictor: z.boolean().default(false),
  constant: z.record(z.any()).default({}),
  default: z.record(z.any()).default({}),
  search: z.object({
    grid: z.record(z.array(z.any())).optional(),
    params: z.record(z.any()).optional(),
  }).optional(),
});

export type ModelConfig = z.infer<typeof MODEL_CONFIG_SCHEMA>;

export async function scanModels(): Promise<Record<string, ModelConfig>> {
  let model_dir = import.meta.resolve("../../models");
  model_dir = fromFileUrl(model_dir);
  let models: Record<string, ModelConfig> = {};
  let files = await Array.fromAsync(Deno.readDir(model_dir));
  files = sortBy(files, (f) => f.name);
  for (let ent of files) {
    let pp = parse(ent.name);
    let text = await Deno.readTextFile(join(model_dir, ent.name));
    let cfg = parseToml(text);
    let mod = MODEL_CONFIG_SCHEMA.parse(cfg);
    if (mod.enabled) {
      models[pp.name] = mod;
    }
  }
  return models;
}

export const MODELS = await scanModels();
