{
  spec:: {
    name: 'ML25M',
    fn: 'ml-25m',
    template: '../_template',
    splits: ['temporal'],
    searches: ['optuna'],
    search_frozen: true,
  },
} + import '../layout.libsonnet'
