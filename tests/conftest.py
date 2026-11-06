"""Session-scoped Node.js golden-master CLI fixture.

Starts golden/emit_cli.ts once (Node's TS type-stripping costs ~0.5s per
process) and feeds it one JSON request per line for the whole test session,
instead of paying that cost once per test case.

Set SVG_DIAGRAM_GOLDEN_RECORD to a file path to additionally dump every
(request, result) pair seen during the session as a JSON object, keyed by
the request's canonical (sort_keys=True) JSON encoding. This is how the
static fixtures consumed by a Node-less checkout of this test suite are
produced; see svg-diagram-py's golden fixture docs for the regeneration
command. A request Node.js itself rejects is recorded as
{"__error__": "<message>"} so that a static replay can reproduce the same
RuntimeError.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_PY_DIR = _TESTS_DIR.parent
_REPO_ROOT = _PY_DIR.parent
_EMIT_CLI = _PY_DIR / "golden" / "emit_cli.ts"


class NodeGolden:
    def __init__(self, record_path: str | None) -> None:
        self.proc = subprocess.Popen(
            ["node", str(_EMIT_CLI)],
            cwd=_REPO_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._record_path = Path(record_path) if record_path else None
        self._record: dict[str, object] = {}

    def call(self, req: dict) -> object:
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(f"golden/emit_cli.ts produced no output for {req!r} (stderr: {err})")
        resp = json.loads(line)
        if not resp["ok"]:
            if self._record_path is not None:
                self._record[json.dumps(req, sort_keys=True)] = {"__error__": resp["error"]}
            raise RuntimeError(f"golden/emit_cli.ts error for {req!r}: {resp['error']}")
        result = resp["result"]
        if self._record_path is not None:
            self._record[json.dumps(req, sort_keys=True)] = result
        return result

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        self.proc.wait(timeout=5)
        if self._record_path is not None:
            self._record_path.parent.mkdir(parents=True, exist_ok=True)
            self._record_path.write_text(
                json.dumps(self._record, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
            )


@pytest.fixture(scope="session")
def node_golden():
    g = NodeGolden(os.environ.get("SVG_DIAGRAM_GOLDEN_RECORD"))
    yield g
    g.close()
