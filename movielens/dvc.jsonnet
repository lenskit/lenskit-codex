local lib = import '../src/lib.libsonnet';
local datasets = [
  'ML100K',
  'ML1M',
  'ML10M',
  'ML20M',
  'ML25M',
  'ML32M ',
];

{
  stages: {
    'aggregate-rating-stats': {
      cmd: lib.action_cmd([
        'movielens aggregate',
        '-d merged-stats.duckdb',
      ] + datasets),
      deps: [
        std.format('%s/stats.duckdb', [ds])
        for ds in datasets
      ],
      outs: ['merged-stats.duckdb'],
    },
  },
}
