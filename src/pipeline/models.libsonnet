local models = std.parseJson(importstr '../../manifests/models.json');

local modelIsActive(mod, ds) =
  local inc = std.get(mod, 'ds_include');
  if inc == null then true
  else std.any([std.native('fnmatch')(ds, g) for g in inc]);

local activeModels(ds) = {
  [m.key]: m.value
  for m in std.objectKeysValues(models)
  if modelIsActive(m.value, ds)
};

{ models: models, activeModels: activeModels }
