local lib = import '../../src/codex.libsonnet';
local data = import '../data.libsonnet';
local results = import '../results.libsonnet';
local runlib = import '../runs.libsonnet';
local sweep = import '../sweeps.libsonnet';

local defs = {
  name:: 'ML1M',
  fn:: 'ml-1m',
  root:: '../..',
};

local runs = runlib.crossfold(defs.name, 'random');

{
  stages: defs
          + data.prepare
          + data.crossfold
          + sweep.crossfold(defs.name, 'random')
          + runlib.stages('../..', runs)
          + results.collect(runs),
  extraFiles: {
    'runs/manifest.csv': runlib.runManifest(runs),
  },
}
