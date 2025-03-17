local lib = import '../../src/lib.libsonnet';
local data = import '../data.libsonnet';
local results = import '../results.libsonnet';
local runlib = import '../runs.libsonnet';

local defs = {
  name:: 'ML1M',
  fn:: 'ml-1m',
  root:: '../..',
};

local runs = runlib.crossfold(defs.root, defs.name);

{
  stages: defs
          + data.prepare
          + data.crossfold
          + runlib.stages('../..', runs)
          + results.collect(runs),
}
