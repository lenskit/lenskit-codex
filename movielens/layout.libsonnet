local lib = import '../src/codex.libsonnet';
local data = import 'data.libsonnet';

local makeRuns(spec) = std.flattenArrays([
  lib.runsForSplit(
    spec,
    split,
    if split == 'random' then 'parquet' else 'toml',
  )
  for split in spec.splits
]);

{
  local spec = lib.search_defaults + super.spec,
  local runs = makeRuns(spec),

  info: spec {
    models: std.sort(std.objectFields(lib.activeModels(spec.name))),
  },
  page_templates: std.get(spec, 'template', default=null),

  stages: data.prepare(spec)
          + lib.allSweepStages(spec)
          + lib.runStages(runs)
          + lib.collectRuns(runs),
  extra_files: {
    'runs/manifest.csv': lib.runManifest(runs),
  },
}
