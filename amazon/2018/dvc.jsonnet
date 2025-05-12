local lib = import '../../src/codex.libsonnet';
// local categories = std.parseYaml(importstr 'categories.yml');
local categories = {};

local cat_pipes = {
  [m.key + '/dvc.yaml']: {
    stages: {
      'import': {
        local src = std.format('../data/%s.csv.zst', [m.value]),
        cmd: lib.lenskit_cmd(['data', 'convert', '--amazon', src, 'dataset']),
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
