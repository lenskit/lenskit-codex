{
  spec:: {
    name: 'MLLT',
    fn: 'ml-latest',
    template: '../_template',
    splits: ['temporal'],
    searches: ['optuna'],
  },
} + import '../layout.libsonnet'
