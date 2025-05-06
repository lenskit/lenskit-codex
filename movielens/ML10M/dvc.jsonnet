{
  spec:: {
    name: 'ML10M',
    fn: 'ml-10m',
    splits: ['temporal'],
    searches: ['random', 'hyperopt', 'optuna'],
    search_points: 100,
    search_frozen: true,
    template: '../_template',
  },
} + import '../layout.libsonnet'
