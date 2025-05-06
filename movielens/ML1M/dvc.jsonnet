{
  spec:: {
    name: 'ML1M',
    fn: 'ml-1m',
    template: '../_template',
    splits: ['random'],
    searches: ['random', 'hyperopt', 'optuna'],
    search_points: 100,
    search_frozen: true,
  },
} + import '../layout.libsonnet'
