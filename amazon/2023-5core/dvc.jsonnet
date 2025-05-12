local lib = import '../../src/codex.libsonnet';
local categories = std.parseYaml(importstr 'categories.yml');

local cat_pipes = {
  [m.key + '/dvc.yaml']: {
    stages: {
      'import-valid-train': {
        local src = std.format('../data/%s.train.csv.gz', [m.value]),
        cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', src, 'dataset.valid']),
        deps: [src],
        outs: ['dataset.valid'],
      },
      'import-full-train': {
        local train = std.format('../data/%s.train.csv.gz', [m.value]),
        local valid = std.format('../data/%s.valid.csv.gz', [m.value]),
        cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', train, valid, 'dataset']),
        deps: [train, valid],
        outs: ['dataset'],
      },
    },
  }
  for m in std.objectKeysValues(categories)
};

{
  stages: {},
  extra_files: cat_pipes,
}
