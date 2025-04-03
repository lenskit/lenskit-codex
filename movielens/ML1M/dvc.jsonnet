{
  spec:: {
    name: 'ML1M',
    fn: 'ml-1m',
    splits: ['random'],
    searches: ['random', 'hyperopt'],
  },
} + import '../layout.libsonnet'
