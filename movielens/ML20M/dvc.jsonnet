local lib = import '../../src/codex.libsonnet';
local data = import '../data.libsonnet';
local results = import '../results.libsonnet';
local runlib = import '../runs.libsonnet';

local defs = {
  name:: 'ML20M',
  fn:: 'ml-20m',
  root:: '../..',
};

local runs = runlib.temporal(defs.name);

{
  stages: defs
          + data.prepare
          + runlib.stages('../..', runs)
          + results.collect(runs),
  extraFiles: {
    'runs/manifest.csv': runlib.runManifest(runs),
  },
}
