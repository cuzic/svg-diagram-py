"""Static Node.js golden-master fixtures.

This checkout has no Node.js source to compare against (that lives in the
private svg-diagram monorepo this port was extracted from), so `node_golden`
looks up each request in golden/fixtures/node_golden_recorded.json instead
of running Node.js live. See golden/README.md for how that file was
produced and how to regenerate it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_RECORDED_FIXTURES = _TESTS_DIR.parent / "golden" / "fixtures" / "node_golden_recorded.json"


class StaticGolden:
    def __init__(self) -> None:
        self._data: dict[str, object] = json.loads(_RECORDED_FIXTURES.read_text(encoding="utf-8"))

    def call(self, req: dict) -> object:
        key = json.dumps(req, sort_keys=True)
        try:
            result = self._data[key]
        except KeyError:
            raise KeyError(
                f"no recorded golden fixture for {req!r}; see golden/README.md to regenerate "
                "node_golden_recorded.json"
            ) from None
        if isinstance(result, dict) and "__error__" in result:
            raise RuntimeError(f"recorded golden error for {req!r}: {result['__error__']}")
        return result


@pytest.fixture(scope="session")
def node_golden():
    return StaticGolden()
