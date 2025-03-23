local lib = import '../../src/codex.libsonnet';
local data = import '../data.libsonnet';
local results = import '../results.libsonnet';
local runlib = import '../runs.libsonnet';
local sweep = import '../sweeps.libsonnet';

local defs = {
  name:: 'ML10M',
  fn:: 'ml-10m',
  root:: '../..',
};

local runs = runlib.temporal(defs.name);

{
  stages: defs
          + data.prepare
          + sweep.temporal(defs.name, 'random')
          + runlib.stages('../..', runs)
          + results.collect(runs),
  extraFiles: {
    'runs/manifest.csv': runlib.runManifest(runs),
  },
}
