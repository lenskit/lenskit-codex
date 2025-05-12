local cmds = import './commands.libsonnet';
local models = import './models.libsonnet';

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

{
  search_defaults: search_defaults,

  allSweepStages(spec_in):
    local spec = search_defaults + spec_in;
    {

      [std.join('-', ['sweep', m.key, split, method])]: {
        local out_dir = std.format('sweeps/%s/%s-%s', [split, m.key, method]),

        cmd: cmds.codex_cmd([
          'search',
          '--split=splits/' + split + (if split == 'fixed' then '' else '.toml'),
          if split == 'random' then '--test-part=0' else '--test-part=valid',
          searchPointsArg(spec, m.value),
          '--' + method,
          if m.value.predictor then '--metric=RMSE' else '--metric=RBP',
          m.key,
          out_dir,
        ]),
        params: if spec.search_points == null then [
          { '../../config.toml': [std.format('tuning.%s.points', [method])] },
        ] else [],
        deps: [
          std.format('splits/%s.%s', [
            split,
            if split == 'random' then 'parquet' else 'toml',
          ]),
          '../../' + m.value.src_path,
        ],
        outs: [
          out_dir,
          { [out_dir + '.json']: { cache: false } },
        ],
      } + if spec.search_frozen then { frozen: true } else {}
      for split in spec.splits
      for method in spec.searches
      for m in std.objectKeysValues(models.activeModels(spec.name))
      if m.value.searchable
    },
}
