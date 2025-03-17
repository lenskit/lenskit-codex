local lib = import '../../src/lib.libsonnet';
local data = import '../data.libsonnet';
local results = import '../results.libsonnet';
local runlib = import '../runs.libsonnet';

local defs = {
  name:: 'ML100K',
  fn:: 'ml-100k',
  root:: '../..',
};

local runs = runlib.crossfold(defs.name, 'random');

{
  stages: defs
          + data.prepare
          + data.crossfold
          + runlib.stages('../..', runs)
          + results.collect(runs),
  extraFiles: {
    'runs/manifest.csv': runlib.runManifest(runs),
  },
}
