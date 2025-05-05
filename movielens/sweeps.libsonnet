local lib = import '../src/codex.libsonnet';

local searchPointsArg(spec, model) =
  local spec_pts = std.get(spec, 'search_points');
  local model_pts = std.get(model, 'search_points');
  if spec_pts != null && model_pts != null then
    std.format('--sample-count=%s', std.min(spec_pts, model_pts))
  else if spec_pts != null then
    std.format('--sample-count=%s', spec_pts)
;

{
  allSweepStages(spec): {
    [std.join('-', ['sweep', m.key, split, method])]: {
      local out_dir = std.format('sweeps/%s/%s-%s', [split, m.key, method]),

      cmd: lib.codex_cmd([
        'search',
        std.format('--split=splits/%s.toml', [split]),
        if split == 'random' then '--test-part=0' else '--test-part=valid',
        searchPointsArg(spec, m.value),
        '--' + method,
        if m.value.predictor then '--metric=RMSE' else '--metric=RBP',
        m.key,
        out_dir,
      ]),
      params: if !std.objectHas(spec, 'search_points') then [
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
    }
    for split in spec.splits
    for method in spec.searches
    for m in std.objectKeysValues(lib.activeModels(spec.name))
    if m.value.searchable
  },
}
