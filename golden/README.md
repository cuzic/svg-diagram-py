# golden/

Fixtures the test suite compares Python's output against, byte-for-byte.

- `fixtures/*_example.json` (curve/pyramid/svg_wrapper): captured once by hand
  from a real Node.js `emitSvg`/layout call, each documenting in its own
  `_comment`/`_capturedFrom` fields exactly what produced it.
- `fixtures/node_golden_recorded.json`: a single request→result map for
  every case the `node_golden` pytest fixture (`tests/conftest.py`) is asked
  for across the whole suite (box/connect/badge/tag/.../route-search/etc.).
  Keyed by each request dict's canonical (`json.dumps(req, sort_keys=True)`)
  encoding.

This is a standalone extraction of the Python port from the private
svg-diagram (TypeScript) monorepo, which has no Node.js source here to
compare against. `node_golden_recorded.json` was produced from inside that
monorepo by running its `py/` test suite with recording turned on:

```sh
SVG_DIAGRAM_GOLDEN_RECORD=/path/to/node_golden_recorded.json uv run pytest
```

(see that monorepo's `py/tests/conftest.py` for the `NodeGolden` CLI
subprocess this drives — `golden/emit_cli.ts` there imports the actual
`lib/*.ts` drawing-layer functions and serves them over a JSON-lines
protocol). The resulting file is then copied here as-is. Regenerating it
is only possible from that monorepo; this repository does not vendor the
Node.js side.
