{
  spec:: {
    name: 'ML10M',
    fn: 'ml-10m',
    splits: ['temporal'],
    searches: ['random', 'hyperopt', 'optuna'],
    search_points: 100,
    template: '../_template',
  },
} + import '../layout.libsonnet'
