local lib = import '../src/codex.libsonnet';
local data = import 'data.libsonnet';
local results = import 'results.libsonnet';
local runlib = import 'runs.libsonnet';
local sweep = import 'sweeps.libsonnet';

{
  local spec = sweep.search_defaults + super.spec,
  local runs = runlib.makeRuns(spec),

  info: spec {
    models: std.sort(std.objectFields(lib.activeModels(spec.name))),
  },
  page_templates: std.get(spec, 'template', default=null),

  stages: data.prepare(spec)
          + sweep.allSweepStages(spec)
          + runlib.stages('../..', runs)
          + results.collect(runs),
  extra_files: {
    'runs/manifest.csv': runlib.runManifest(runs),
  },
}
