"""Session-scoped Node.js golden-master CLI fixture.

Starts golden/emit_cli.ts once (Node's TS type-stripping costs ~0.5s per
process) and feeds it one JSON request per line for the whole test session,
instead of paying that cost once per test case.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_PY_DIR = _TESTS_DIR.parent
_REPO_ROOT = _PY_DIR.parent
_EMIT_CLI = _PY_DIR / "golden" / "emit_cli.ts"


class NodeGolden:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            ["node", str(_EMIT_CLI)],
            cwd=_REPO_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

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
            raise RuntimeError(f"golden/emit_cli.ts error for {req!r}: {resp['error']}")
        return resp["result"]

    def close(self) -> None:
        if self.proc.stdin:
            self.proc.stdin.close()
        self.proc.wait(timeout=5)


@pytest.fixture(scope="session")
def node_golden():
    g = NodeGolden()
    yield g
    g.close()
