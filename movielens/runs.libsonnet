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

local runsForSplit(spec, split) =
  local splitDep =
    if split == 'random'
    then std.format('splits/%s.parquet', [split])
    else std.format('splits/%s.toml', [split]);
  [
    {
      name: std.format('run-%s-default-%s', [split, model]),
      dataset: spec.name,
      args: ['--default'],
      model: model,
      split: split,
      variant: 'default',
      deps: ['dataset', splitDep],
    }
    for model in std.objectFields(lib.activeModels(spec.name))
  ] + [
    {
      local model = m.key,
      local params = std.format('sweeps/%s/%s-%s.json', [split, model, search]),

      name: std.format('run-%s-%s-best-%s', [split, search, model]),
      dataset: spec.name,
      args: ['--param-file', params],
      model: model,
      split: split,
      variant: search + '-best',
      deps: [
        'dataset',
        splitDep,
        params,
      ],
    }
    for search in spec.searches
    for m in std.objectKeysValues(lib.activeModels(spec.name))
    if m.value.searchable
  ];

local makeRuns(spec) =
  std.flattenArrays([
    runsForSplit(spec, split)
    for split in spec.splits
  ]);

{
  makeRuns: makeRuns,
  stages: runStages,
  runPath: runPath,
  runManifest: runManifest,
}
