local lib = import '../../lib.jsonnet';
local meta = std.parseYaml(importstr 'meta.yml');

local ml_import = function(name, fn) {
  cmd: std.format('python ../import-ml.py %s.zip', [fn]),
  deps: [
    '../import-ml.py',
    '../../codex/rating_stat_views.sql',
    fn + '.zip',
  ],
  outs: [
    'ratings.parquet',
  ],
};

local ml_pipeline = function(name) {
  local fn = meta.datasets[name],
  stages: {
    ['import-' + fn]: ml_import(name, fn),
  },
};

{
  subdirs: {
    [name]: ml_pipeline(name)
    for name in std.objectFields(meta.datasets)
  },
}
