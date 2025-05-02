{
  spec:: {
    name: 'ML100K',
    fn: 'ml-100k',
    template: '../_template',
    splits: ['random'],
    searches: ['random', 'hyperopt', 'optuna'],
  },
} + import '../layout.libsonnet'
