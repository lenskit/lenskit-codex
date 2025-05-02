{
  spec:: {
    name: 'ML20M',
    fn: 'ml-20m',
    template: '../_template',
    splits: ['temporal'],
    searches: ['random', 'hyperopt', 'optuna'],
  },
} + import '../layout.libsonnet'
