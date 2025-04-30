{
  spec:: {
    name: 'ML20M',
    fn: 'ml-20m',
    splits: ['temporal'],
    searches: ['random', 'hyperopt'],
  },
} + import '../layout.libsonnet'
