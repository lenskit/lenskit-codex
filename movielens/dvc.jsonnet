local lib = import '../../lib.jsonnet';
local meta = std.parseYaml(importstr 'meta.yml');
local ds_names = std.objectFields(meta.datasets);

local ml_import = function(name, fn) {
  cmd: std.format('python ../import-ml.py %s.zip', [fn]),
  deps: [
    '../import-ml.py',
    fn + '.zip',
  ],
  outs: [
    'ratings.parquet',
  ],
};
local ml_stats = function(name) {
  cmd: 'python ../../scripts/duckdb-sql.py -d stats.duckdb ../ml-stats.sql',
  deps: [
    '../ml-stats.sql',
    'ratings.parquet',
  ],
  outs: [
    'stats.duckdb',
  ],
};

local ml_pipeline = function(name) {
  local fn = meta.datasets[name],
  stages: {
    ['import-' + fn]: ml_import(name, fn),
    [fn + '-stats']: ml_stats(name),
  },
};

{
  subdirs: {
    [name]: ml_pipeline(name)
    for name in ds_names
  },
}
