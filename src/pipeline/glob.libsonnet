local splitComponents(gs, indices, offset) =
  if std.length(indices) > 0
  then (local pos = indices[0] - offset; [gs[0:pos], { star: true }] + splitComponents(gs[(pos + 1):], indices[1:], pos + 1))
  else [gs];

local parseGlob(glob) =
  local indices = std.findSubstr('*', glob);
  std.filter(function(p) p != '', splitComponents(glob, indices, 0));

local matchGlobParts(parts, str) =
  if std.length(parts) == 0
  then std.length(str) == 0
  else if std.length(str) == 0
  then false
  // fast-path final stars
  else local part = parts[0];
       if std.length(parts) == 1 && std.type(part) == 'object'
  then true
  else if std.type(part) == 'string'
  then (
    std.startsWith(str, part)
    && matchGlobParts(parts[1:], str[std.length(part):])
  )
  else matchGlobParts(parts[1:], str) || matchGlobParts(parts, str[1:]);

local matchGlob(glob, str) =
  local parts = parseGlob(glob);
  matchGlobParts(parts, str);

{ matchGlob: matchGlob }
