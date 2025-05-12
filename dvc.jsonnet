local lib = import 'src/codex.libsonnet';

local docs = std.parseJson(importstr 'manifests/documents.json');

{
  stages: {
    // create a stage to pre-render each page
    [std.format('page/%s', [lib.removeSuffix(doc.key)])]: {
      local dir = lib.dirname(doc.key),

      cmd: std.format('quarto render %s', [doc.key]),
      deps: [
        '_quarto.yml',
        doc.key,
      ] + [
        lib.resolvePath(dir, dep)
        for dep in std.get(doc.value, 'deps', [])
      ],
      outs: [
        std.format('_freeze/%s', [lib.removeSuffix(doc.key)]),
      ] + [
        lib.resolvePath(dir, out)
        for out in std.get(doc.value, 'outs', [])
      ],
    }
    for doc in std.objectKeysValues(docs)
  },
}
