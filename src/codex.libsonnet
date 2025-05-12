local cmdlib = import 'pipeline/commands.libsonnet';
local models = import 'pipeline/models.libsonnet';
local pathlib = import 'pipeline/paths.libsonnet';
local results = import 'pipeline/results.libsonnet';
local runs = import 'pipeline/runs.libsonnet';
local sweeps = import 'pipeline/sweeps.libsonnet';

local contains(arr, elt) =
  if std.length(arr) == 0
  then false
  else if arr[0] == elt
  then true
  else contains(arr[1:], elt);

local fnmatch(name, pattern) = std.native(fnmatch)(name, pattern);


pathlib + cmdlib + models + runs + sweeps + results + {
  fnmatch: fnmatch,
  contains: contains,
}
