local lib = import '../src/codex.libsonnet';

local runPath(run) =
  std.format('%s/%s-%s', [run.split, run.model, run.variant]);
local runStages(origin, runs) =
  {
    [run.name]: {
      local path = runPath(run),
      cmd: lib.codex_cmd(['generate'] + run.args + [
        '--ds-name=' + run.dataset,
        std.format('--split=splits/%s.toml', [run.split]),
        '-o runs/' + path,
        run.model,
      ]),
      outs: ['runs/' + path],
      deps: [std.format('%s/src/codex/models/%s.py', [origin, std.strReplace(run.model, '-', '_')])] + std.get(run, 'deps', []),
    }
    for run in runs
  };

local runManifest(runs) = std.join('\n', [
  'path,split,variant,model',
] + [
  std.join(',', [runPath(run), run.split, run.variant, run.model])
  for run in runs
] + ['']);

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
  for model in std.objectFields(lib.activeModels(dataset))
] + [
  {
    local model = m.key,
    local params = std.format('sweeps/%s/%s-random.json', [split, model]),

    name: std.format('run-%s-random-best-%s', [split, model]),
    dataset: dataset,
    args: ['--param-file', params],
    model: model,
    split: split,
    variant: 'random-best',
    deps: [
      'dataset',
      std.format('splits/%s.parquet', [split]),
      params,
    ],
  }
  for m in std.objectKeysValues(lib.activeModels(dataset))
  if m.value.searchable
];

local splitRuns(dataset, split='temporal') = [
  {
    name: std.format('run-%s-default-%s', [split, model]),
    dataset: dataset,
    args: ['--default'],
    model: model,
    split: split,
    variant: 'default',
    deps: ['dataset', std.format('splits/%s.toml', [split])],
  }
  for model in std.objectFields(lib.activeModels(dataset))
] + [
  {
    local model = m.key,
    local params = std.format('sweeps/%s/%s-random.json', [split, model]),

    name: std.format('run-%s-random-best-%s', [split, model]),
    dataset: dataset,
    args: ['--param-file', params],
    model: model,
    split: split,
    variant: 'random-best',
    deps: [
      'dataset',
      std.format('splits/%s.toml', [split]),
      params,
    ],
  }
  for m in std.objectKeysValues(lib.activeModels(dataset))
  if m.value.searchable
];

{
  crossfold: crossfoldRuns,
  temporal: splitRuns,
  stages: runStages,
  runPath: runPath,
  runManifest: runManifest,
}
