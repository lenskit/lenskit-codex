{
  spec:: {
    name: 'ML100K',
    fn: 'ml-100k',
    splits: ['random'],
    searches: ['random', 'hyperopt', 'optuna'],
  },
} + import '../layout.libsonnet'
