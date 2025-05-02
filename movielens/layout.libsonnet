local lib = import '../src/codex.libsonnet';
local data = import 'data.libsonnet';
local results = import 'results.libsonnet';
local runlib = import 'runs.libsonnet';
local sweep = import 'sweeps.libsonnet';

{
  local spec = super.spec,
  local runs = runlib.makeRuns(spec),

  stages: data.prepare(spec)
          + sweep.allSweepStages(spec)
          + runlib.stages('../..', runs)
          + results.collect(runs),
  extraFiles: {
    'dataset.yml': std.manifestYamlDoc(spec, quote_keys=false),
    'runs/manifest.csv': runlib.runManifest(runs),
  },
}
