{
  lenskit_cmd: function(parts)
    std.join(' ', ['lenskit'] + parts),
  codex_cmd: function(parts)
    std.join(' ', ['lenskit', 'codex'] + parts),
}
