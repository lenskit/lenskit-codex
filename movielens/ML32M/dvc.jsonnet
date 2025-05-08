{
  spec:: {
    name: 'ML32M',
    fn: 'ml-32m',
    template: '../_template',
    splits: ['temporal'],
    searches: ['optuna'],
    search_frozen: true,
  },
} + import '../layout.libsonnet'
