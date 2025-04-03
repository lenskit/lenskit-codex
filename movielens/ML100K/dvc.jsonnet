{
  spec:: {
    name: 'ML100K',
    fn: 'ml-100k',
    splits: ['random'],
    searches: ['random', 'hyperopt'],
  },
} + import '../layout.libsonnet'
