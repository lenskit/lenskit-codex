local cmds = import './commands.libsonnet';
local models = import './models.libsonnet';
local paths = import './paths.libsonnet';

local runPath(run) =
  std.format('%s/%s-%s', [run.split, run.model, run.variant]);
local runStages(runs, subdir=null) =
  local root = if subdir == null then paths.projectRoot else '../' + paths.projectRoot;
  {
    ['run-' + run.name]: {
      local path = runPath(run),
      cmd: cmds.codex_cmd(['generate'] + run.args + [
        '--ds-name=' + run.dataset,
        '--split=splits/' + run.split + (if run.split == 'fixed' then '' else '.toml'),
        '-o runs/' + path,
        run.model,
      ]),
      outs: ['runs/' + path],
      deps: [std.format('%s/src/codex/models/%s.py', [root, std.strReplace(run.model, '-', '_')])] + std.get(run, 'deps', []),
    }
    for run in runs
  };

local runManifest(runs) = std.join('\n', [
  'path,split,variant,model',
] + [
  std.join(',', [runPath(run), run.split, run.variant, run.model])
  for run in runs
] + ['']);

local runsForSplit(spec, split, dep_type) =
  local deps =
    if dep_type == 'parquet'
    then ['dataset', std.format('splits/%s.parquet', [split])]
    else if dep_type == 'toml'
    then ['dataset', std.format('splits/%s.toml', [split])]
    else [std.format('splits/%s', [split])];
  [
    {
      name: std.format('%s-default-%s', [split, model]),
      dataset: spec.name,
      args: ['--default'],
      model: model,
      split: split,
      variant: 'default',
      deps: deps,
    }
    for model in std.objectFields(models.activeModels(spec.name))
  ] + [
    {
      local model = m.key,
      local params = std.format('sweeps/%s/%s-%s.json', [split, model, search]),

      name: std.format('%s-%s-best-%s', [split, search, model]),
      dataset: spec.name,
      args: ['--param-file', params],
      model: model,
      split: split,
      variant: search + '-best',
      deps: deps + [params],
    }
    for search in spec.searches
    for m in std.objectKeysValues(models.activeModels(spec.name))
    if m.value.searchable
  ];


{
  runsForSplit: runsForSplit,
  runStages: runStages,
  runPath: runPath,
  runManifest: runManifest,
}
