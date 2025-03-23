local lib = import '../src/codex.libsonnet';
local runlib = import './runs.libsonnet';


{
  collect: function(runs) {
    'collect-metrics': {
      cmd: lib.codex_cmd([
        'collect metrics',
        '-S run-summary.csv',
        '-U run-user-metrics.parquet',
        '-L runs/manifest.csv',
      ]),
      deps: [
        'runs/' + runlib.runPath(run)
        for run in runs
      ],
      outs: ['run-summary.csv', 'run-user-metrics.parquet'],
    },
  },
}
