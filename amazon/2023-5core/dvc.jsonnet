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
    } + lib.runStages(runs),
  }
  for m in std.objectKeysValues(categories)
};

{
  stages: {},
  extra_files: cat_pipes,
}
