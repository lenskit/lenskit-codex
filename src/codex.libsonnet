local cmdlib = import 'pipeline/commands.libsonnet';
local glob = import 'pipeline/glob.libsonnet';
local models = import 'pipeline/models.libsonnet';
local pathlib = import 'pipeline/paths.libsonnet';

local contains(arr, elt) =
  if std.length(arr) == 0
  then false
  else if arr[0] == elt
  then true
  else contains(arr[1:], elt);


pathlib + cmdlib + models + glob + {
  contains: contains,
}
