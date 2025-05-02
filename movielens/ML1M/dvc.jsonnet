{
  spec:: {
    name: 'ML1M',
    fn: 'ml-1m',
    template: '../_templates',
    splits: ['random'],
    searches: ['random', 'hyperopt'],
  },
} + import '../layout.libsonnet'
