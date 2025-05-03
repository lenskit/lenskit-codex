{
  spec:: {
    name: 'ML1M',
    fn: 'ml-1m',
    template: '../_template',
    splits: ['random'],
    searches: ['random', 'hyperopt', 'optuna'],
  },
} + import '../layout.libsonnet'
