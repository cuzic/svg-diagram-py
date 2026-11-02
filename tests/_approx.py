"""A tolerant structural comparator for golden tests, for the rare fields where a
cross-engine floating-point ULP difference (e.g. V8's Math.hypot vs CPython's math.hypot,
see plane.py's module docstring) can show up in pre-render layout data without ever
affecting the rendered output. Degrades to normal equality for non-numeric values, so it is
safe to use everywhere a golden test compares a layout dict, not just where ULP drift is
known to occur.
"""

from __future__ import annotations

import math


def approx(a, b, tol: float = 1e-9) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(approx(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(approx(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
    return a == b
