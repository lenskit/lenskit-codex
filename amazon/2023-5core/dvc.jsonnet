local lib = import '../../src/codex.libsonnet';
local categories = std.parseYaml(importstr 'categories.yml');


local cat_pipes = {
  [m.key + '/dvc.yaml']: {
    local spec = {
      name: m.key,
      splits: ['fixed'],
      searches: ['optuna'],
    },
    local runs = lib.runsForSplit(spec, 'fixed', 'dir'),

    stages: {
      'import-valid-train': {
        local src = std.format('../data/%s.train.csv.gz', [m.value]),
        cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', src, 'splits/fixed/valid/train.dataset']),
        deps: [src],
        outs: ['splits/fixed/valid/train.dataset'],
      },
      'import-valid-test': {
        local src = std.format('../data/%s.valid.csv.gz', [m.value]),
        cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', '--item-lists', src, 'splits/fixed/valid/test.parquet']),
        deps: [src],
        outs: ['splits/fixed/valid/test.parquet'],
      },
      'import-test-train': {
        local train = std.format('../data/%s.train.csv.gz', [m.value]),
        local valid = std.format('../data/%s.valid.csv.gz', [m.value]),
        cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', train, valid, 'splits/fixed/test/train.dataset']),
        deps: [train, valid],
        outs: ['splits/fixed/test/train.dataset'],
      },
      'import-test-test': {
        local src = std.format('../data/%s.test.csv.gz', [m.value]),
        cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', '--item-lists', src, 'splits/fixed/test/test.parquet']),
        deps: [src],
        outs: ['splits/fixed/test/test.parquet'],
      },

      'export-valid-qrels': {
        cmd: lib.codex_cmd(['trec', 'export', 'qrels', '-o', 'splits/fixed/valid.qrels.gz', 'splits/fixed/valid/test.parquet']),
        deps: ['splits/fixed/valid/test.parquet'],
        outs: ['splits/fixed/valid.qrels.gz'],
      },
      'export-test-qrels': {
        cmd: lib.codex_cmd(['trec', 'export', 'qrels', '-o', 'splits/fixed/test.qrels.gz', 'splits/fixed/test/test.parquet']),
        deps: ['splits/fixed/test/test.parquet'],
        outs: ['splits/fixed/test.qrels.gz'],
      },
    } + lib.allSweepStages(spec, m.key) + lib.runStages(runs, m.key) + lib.collectRuns(runs),
  }
  for m in std.objectKeysValues(categories)
};

{
  stages: {},
  extra_files: cat_pipes,
}
