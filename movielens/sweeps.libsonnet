local lib = import '../src/lib.libsonnet';

local sweepStages(split, method, split_type) =
  {
    [std.join('-', ['sweep', m.key, split, method])]: {
      local out_dir = std.format('sweeps/%s/%s-%s', [split, m.key, method]),

      cmd: lib.codex_cmd([
        'search',
        std.format('--split=splits/%s.toml', [split]),
        '--test-part=0',
        if method == 'random' then '--random',
        if m.value.predictor then '--metric=RMSE' else '--metric=RBP',
        m.key,
        out_dir,
      ]),
      deps: [
        std.format('splits/%s.%s', [
          split,
          if split_type == 'random' then 'parquet' else 'toml',
        ]),
        '../../..' + m.value.src_path,
      ],
      outs: [
        out_dir,
      ],
    }
    for m in std.objectKeysValues(lib.models)
  };

{
  crossfold: function(method) sweepStages('random', method, 'random'),
  temporal: function(method) sweepStages('temporal', method, 'temporal'),
}
