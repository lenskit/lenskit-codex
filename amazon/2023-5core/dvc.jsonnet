local lib = import '../../src/codex.libsonnet';
local categories = std.parseYaml(importstr 'categories.yml');

local cat_pipes = {
  [m.key + '/dvc.yaml']: {
    stages: {
      'import': {
        local src = std.format('../data/%s.train.csv.gz', [m.value]),
        cmd: lib.codex_cmd(['amazon', 'import-train', '-o', 'dataset', src]),
        deps: [src],
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
