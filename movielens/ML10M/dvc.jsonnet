{
  spec:: {
    name: 'ML10M',
    fn: 'ml-10m',
    splits: ['temporal'],
    searches: ['random', 'hyperopt', 'optuna'],
    template: '../_template',
  },
} + import '../layout.libsonnet'
