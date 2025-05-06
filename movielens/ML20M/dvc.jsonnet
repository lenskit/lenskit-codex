{
  spec:: {
    name: 'ML20M',
    fn: 'ml-20m',
    template: '../_template',
    splits: ['temporal'],
    searches: ['random', 'hyperopt', 'optuna'],
    search_points: 100,
    search_frozen: true,
  },
} + import '../layout.libsonnet'
