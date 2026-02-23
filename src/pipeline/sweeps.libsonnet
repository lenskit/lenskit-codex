local cmds = import './commands.libsonnet';
local models = import './models.libsonnet';
local paths = import './paths.libsonnet';

local search_defaults = {
  searches: ['optuna'],
  search_points: null,
  search_frozen: false,
};

local searchPointsArg(spec, model) =
  local model_pts = std.get(model, 'search_points');
  if spec.search_points != null && model_pts != null then
    std.format('--sample-count=%s', std.min(spec.search_points, model_pts))
  else if spec.search_points != null then
    std.format('--sample-count=%s', spec.search_points)
;

local splitInfo(name) =
  if name == 'fixed' then
    { file: 'splits/fixed', dep: 'splits/fixed/valid' }
  else if name == 'random' then
    { file: 'splits/random.toml', dep: 'splits/random.parquet' }
  else
    { file: std.format('splits/%s.toml', [name]), dep: self.file }
;

{
  search_defaults: search_defaults,

  allSweepStages(spec_in, subdir=null):
    local spec = search_defaults + spec_in;
    local root = if subdir == null then paths.projectRoot else '../' + paths.projectRoot;

    {

      [std.join('-', ['sweep', m.key, split, method])]: {
        local sp = splitInfo(split),
        local out_dir = std.format('sweeps/%s/%s-%s', [split, m.key, method]),

        cmd: cmds.codex_cmd([
          'tune',
          '--split=' + sp.file,
          if split == 'random' then '--test-part=0' else '--test-part=valid',
          searchPointsArg(spec, m.value),
          '--' + method,
          if m.value.predictor then '--metric=RMSE' else '--metric=RBP',
          m.key,
          out_dir,
        ]),
        params: if spec.search_points == null then [
          { [root + '/config.toml']: [std.format('tuning.%s.points', [method])] },
        ] else [],
        deps: [
          sp.dep,
          root + '/' + m.value.src_path,
        ],
        outs: [
          out_dir,
          { [out_dir + '.json']: { cache: false } },
          { [out_dir + '-pipeline.json']: { cache: false } },
        ],
      } + if spec.search_frozen then { frozen: true } else {}
      for split in spec.splits
      for method in spec.searches
      for m in std.objectKeysValues(models.activeModels(spec.name))
      if m.value.searchable
    },
}
