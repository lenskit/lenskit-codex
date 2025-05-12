local lib = import '../src/codex.libsonnet';
local data = import 'data.libsonnet';
local results = import 'results.libsonnet';
local sweep = import 'sweeps.libsonnet';

local makeRuns(spec) = std.flattenArrays([
  lib.runsForSplit(
    spec,
    split,
    if split == 'random' then 'parquet' else 'toml',
  )
  for split in spec.splits
]);

{
  local spec = sweep.search_defaults + super.spec,
  local runs = makeRuns(spec),

  info: spec {
    models: std.sort(std.objectFields(lib.activeModels(spec.name))),
  },
  page_templates: std.get(spec, 'template', default=null),

  stages: data.prepare(spec)
          + sweep.allSweepStages(spec)
          + lib.runStages('../..', runs)
          + results.collect(runs),
  extra_files: {
    'runs/manifest.csv': lib.runManifest(runs),
  },
}
