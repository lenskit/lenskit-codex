{
  spec:: {
    name: 'ML10M',
    fn: 'ml-10m',
    splits: ['temporal'],
    searches: ['random', 'hyperopt'],
  },
} + import '../layout.libsonnet'
