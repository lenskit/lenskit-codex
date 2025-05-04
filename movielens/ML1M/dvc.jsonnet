{
  spec:: {
    name: 'ML1M',
    fn: 'ml-1m',
    template: '../_template',
    splits: ['random'],
    searches: ['random', 'hyperopt', 'optuna'],
    search_points: 100,
  },
} + import '../layout.libsonnet'
