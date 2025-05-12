local cmds = import './commands.libsonnet';
local runs = import './runs.libsonnet';


{
  collectRuns: function(runs) {
    'collect-metrics': {
      cmd: cmds.codex_cmd([
        'collect metrics',
        '-S run-summary.csv',
        '-U run-user-metrics.parquet',
        '-L runs/manifest.csv',
      ]),
      deps: [
        'runs/' + runs.runPath(run)
        for run in runs
      ],
      outs: ['run-summary.csv', 'run-user-metrics.parquet'],
    },
  },
}
