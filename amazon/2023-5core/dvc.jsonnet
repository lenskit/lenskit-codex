local lib = import '../../src/codex.libsonnet';
local categories = std.parseYaml(importstr 'categories.yml');

local categoryPipeline(ds_key, ds_name) = {
  local spec = {
    name: ds_key,
    splits: ['fixed'],
    searches: ['optuna'],
  },
  local runs = lib.runsForSplit(spec, 'fixed', 'dir'),


  stages: {
    'import-valid-train': {
      local src = std.format('../data/%s.train.csv.gz', [ds_name]),
      cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', src, 'splits/fixed/valid/train.dataset']),
      deps: [src],
      outs: ['splits/fixed/valid/train.dataset'],
    },
    'import-valid-test': {
      local src = std.format('../data/%s.valid.csv.gz', [ds_name]),
      cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', '--item-lists', src, 'splits/fixed/valid/test.parquet']),
      deps: [src],
      outs: ['splits/fixed/valid/test.parquet'],
    },
    'import-test-train': {
      local train = std.format('../data/%s.train.csv.gz', [ds_name]),
      local valid = std.format('../data/%s.valid.csv.gz', [ds_name]),
      cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', train, valid, 'splits/fixed/test/train.dataset']),
      deps: [train, valid],
      outs: ['splits/fixed/test/train.dataset'],
    },
    'import-test-test': {
      local src = std.format('../data/%s.test.csv.gz', [ds_name]),
      cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', '--item-lists', src, 'splits/fixed/test/test.parquet']),
      deps: [src],
      outs: ['splits/fixed/test/test.parquet'],
    },

    'export-trec-qrels': {
      foreach: ['test', 'valid'],
      do: {
        cmd: lib.codex_cmd(['trec', 'export', 'qrels', '-o', 'splits/fixed/${item}.qrels.gz', 'splits/fixed/${item}/test.parquet']),
        deps: ['splits/fixed/${item}/test.parquet'],
        outs: ['splits/fixed/${item}.qrels.gz'],
      },
    },
    'export-trec-default-runs': {
      cmd: lib.codex_cmd(['trec', 'export', 'runs', '-o', 'runs/fixed/default.run.gz', 'runs/fixed/*-default']),
      deps: [
        std.format('runs/fixed/%s-default/recommendations.parquet', [model])
        for model in std.objectFields(lib.activeModels(ds_key))
      ],
      outs: ['runs/fixed/default.run.gz'],
    },
  } + lib.allSweepStages(spec, ds_key) + lib.runStages(runs, ds_key) + lib.collectRuns(runs),

  extra_files: {
    'runs/manifest.csv': lib.runManifest(runs),
  },

};

{
  stages: {
    'collect-stats': {
      cmd: lib.codex_cmd(['sql', '-f', 'bench-stats.sql', 'stats.duckdb']),
      outs: ['stats.duckdb'],
      deps: [
        'bench-stats.sql',
      ] + lib.glob('data/*.csv.gz'),
    },
  },
  subdirs: {
    [m.key]: categoryPipeline(m.key, m.value)
    for m in std.objectKeysValues(categories)
  },
}
