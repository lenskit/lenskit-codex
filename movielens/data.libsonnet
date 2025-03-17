local lib = import '../src/lib.libsonnet';

{
  prepare:
    {
      local name = super.name,
      local fn = super.fn,
      local zip = fn + '.zip',

      'import': {
        cmd: lib.lenskit_cmd(['data convert --movielens', zip, 'dataset']),
        deps: [zip],
        outs: ['dataset'],
      },
      stats: {
        cmd: lib.codex_cmd(['sql -D', 'ds_name=' + name, '-f', '../ml-stats.sql', 'stats.duckdb']),
        deps: ['../ml-stats.sql', 'dataset'],
        outs: ['stats.duckdb'],
      },
    },

  crossfold: {
    split:: 'random',
    'split-random': {
      cmd: lib.codex_cmd(['split', 'random.toml']),
      wdir: 'splits',
      params: [{ '../../../config.toml': ['random.seed'] }],
      deps: ['random.toml', '../dataset'],
      outs: ['random.parquet'],
    },
  },
}
