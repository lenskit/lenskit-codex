local lib = import '../src/codex.libsonnet';

{
  allSweepStages(spec): {
    [std.join('-', ['sweep', m.key, split, method])]: {
      local out_dir = std.format('sweeps/%s/%s-%s', [split, m.key, method]),

      cmd: lib.codex_cmd([
        'search',
        std.format('--split=splits/%s.toml', [split]),
        if split == 'random' then '--test-part=0' else '--test-part=valid',
        if std.objectHas(m.value, 'search_points') then std.format('--sample-count=%s', m.value.search_points),
        '--' + method,
        if m.value.predictor then '--metric=RMSE' else '--metric=LogRBP',
        m.key,
        out_dir,
      ]),
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
