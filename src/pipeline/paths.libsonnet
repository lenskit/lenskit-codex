local makeRelativePath = function(pt1, pt2)
  local l1 = std.length(pt1);
  local l2 = std.length(pt2);
  if l1 == 0 || l2 == 0
  then pt1 + pt2
  else if pt2[0] == '.'
  then makeRelativePath(pt1, pt2[1:l2])
  else if pt2[0] == '..'
  then makeRelativePath(pt1[0:l1 - 1], pt2[1:l2])
  else pt1 + pt2;

{
  dirname: function(path)
    local parts = std.split(path, '/');

    std.join('/', parts[0:std.length(parts) - 1]),

  basename: function(path)
    local parts = std.split(path, '/');

    parts[std.length(parts) - 1],

  removeSuffix: function(path)
    local parts = std.splitLimitR(path, '.', 1);
    if std.length(parts) == 2
    then parts[0]
    else path,

  suffix: function(path)
    local parts = std.splitLimitR(path, '.', 1);
    if std.length(parts) == 2
    then parts[1]
    else path,

  relative: function(p1, p2)
    local pt1 = std.split(std.stripChars(p1, '/'), '/');
    local l1 = std.split(std.stripChars(p2, '/'), '/');
    local pt2 = std.split(p2, '/');
    std.join('/', makeRelativePath(pt1, pt2)),
}
