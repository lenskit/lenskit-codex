local lib = import '../src/lib.libsonnet';

local runPath(run) =
  std.format('%s-%s/%s', [run.split, run.variant, run.model]);
local runStages(origin, runs) =
  {
    [run.name]: {
      local path = runPath(run),
      cmd: lib.codex_cmd(['generate'] + run.args + [
        '--ds-name=' + run.dataset,
        std.format('--split=splits/%s.toml', [run.split]),
        '-o runs/' + path,
      ]),
      outs: [path],
      deps: [std.format('%s/models/%s.toml', [origin, run.model])] + std.get(run, 'deps', []),
    }
    for run in runs
  };

local crossfoldRuns(dataset, split) = [
  {
    name: std.format('run-%s-default-%s', [split, model]),
    dataset: dataset,
    args: ['--default'],
    model: model,
    split: split,
    variant: 'default',
    deps: ['dataset', std.format('splits/%s.parquet', [split])],
  }
  for model in std.objectFields(lib.models)
];

local splitRuns(dataset, split) = [
  {
    name: std.format('run-%s-default-%s', [split, model]),
    dataset: dataset,
    args: ['--default'],
    model: model,
    split: split,
    variant: 'default',
    deps: ['dataset', std.format('splits/%s.toml', [split])],
  }
  for model in std.objectFields(lib.models)
];

{
  crossfold: crossfoldRuns,
  temporal: splitRuns,
  stages: function(origin, runs) {
    [run.name]: {
      local path = runPath(run),
      cmd: lib.codex_cmd(['generate'] + run.args + [
        '--ds-name=' + run.dataset,
        std.format('--split=splits/%s.toml', [run.split]),
        '-o runs/' + path,
      ]),
      outs: [path],
      deps: [std.format('%s/models/%s.toml', [origin, run.model])] + std.get(run, 'deps', []),
    }
    for run in runs
  },
  runPath: runPath,
}
