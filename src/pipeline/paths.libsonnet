{
  parsePath: std.native('parse_path'),
  projectRoot: std.native('project_root')(),
  projectPath: std.native('project_path'),

  dirname: function(path)
    self.parsePath(path).dir,

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
    std.native('relpath')(p1, p2),

  resolvePath: std.native('resolve_path'),

  glob: std.native('glob'),
}
