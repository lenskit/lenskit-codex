local lib = import 'src/codex.libsonnet';

local docs = std.parseJson(importstr 'manifests/documents.json');

// create a stage to pre-render each page
{
  stages: {
    [std.format('page/%s', [lib.removeSuffix(doc.key)])]: {
      cmd: std.format('quarto render %s --profile prerender', [doc.key]),
      deps: [
        '_quarto-prerender.yml',
        '_quarto.yml',
        doc.key,
      ] + [
        lib.relative(lib.dirname(doc.key), dep)
        for dep in std.get(doc.value, 'deps', [])
      ],
      outs: [
        std.format('_freeze/%s', [lib.removeSuffix(doc.key)]),
      ] + [
        lib.relative(lib.dirname(doc.key), out)
        for out in std.get(doc.value, 'outs', [])
      ],
    }
    for doc in std.objectKeysValues(docs)
  },
}
