"""1:1 port of lib/polyline-metrics.ts — bends, crossings and length of polylines: pure
functions of points (ADR 0016 D6). The layered layout's candidate score (layered-route.ts,
not yet ported) and the `edge-bends`/`edge-crossings` checks (rules.ts, the check/lint tool,
out of this port's scope) count with these. All exported in Node and golden-tested live.

Golden master: lib/polyline-metrics.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math


def _same(a: dict, b: dict) -> bool:
    return abs(a["x"] - b["x"]) < 0.01 and abs(a["y"] - b["y"]) < 0.01


def simplify(pts: list[dict]) -> list[dict]:
    """lib/polyline-metrics.ts:9-18 simplify(): drops repeated points and the middle point of
    three on a line, so a polyline has only its corners."""
    out: list[dict] = []
    for p in pts:
        if not out or not _same(out[-1], p):
            out.append(p)

    def keep(i: int, p: dict) -> bool:
        if i == 0 or i == len(out) - 1:
            return True
        a, b = out[i - 1], out[i + 1]
        return not ((a["x"] == p["x"] and p["x"] == b["x"]) or (a["y"] == p["y"] and p["y"] == b["y"]))

    return [p for i, p in enumerate(out) if keep(i, p)]


def bends_of(points: list[dict]) -> int:
    """lib/polyline-metrics.ts:21 bendsOf(): the inner points where the line turns (a repeated
    point or a point in the middle of a straight run is not one)."""
    return max(0, len(simplify(points)) - 2)


def total_length(points: list[dict]) -> float:
    """lib/polyline-metrics.ts:24-28 totalLength()."""
    n = 0.0
    for i in range(1, len(points)):
        a, b = points[i], points[i - 1]
        n += math.hypot(a["x"] - b["x"], a["y"] - b["y"])
    return n


def crossings_of(paths: list[list[dict]], margin: float = 0, tol: float = 0) -> int:
    """lib/polyline-metrics.ts:41-66 crossingsOf(): the places where two different polylines
    properly cross at a right angle (a horizontal run against a vertical one). Touching and
    overlapping do not count, nor does a polyline crossing itself. Diagonal segments are not
    counted. `margin`/`tol` match Node's CrossOpts."""
    m = margin

    def level(a: dict, b: dict) -> bool:
        return a["y"] == b["y"] or abs(a["y"] - b["y"]) < tol

    def plumb(a: dict, b: dict) -> bool:
        return a["x"] == b["x"] or abs(a["x"] - b["x"]) < tol

    hs: list[list[dict]] = []
    vs: list[list[dict]] = []
    for p in paths:
        h: list[dict] = []
        v: list[dict] = []
        for i in range(1, len(p)):
            a, b = p[i - 1], p[i]
            if level(a, b):
                h.append({"y": a["y"], "lo": min(a["x"], b["x"]), "hi": max(a["x"], b["x"])})
            if plumb(a, b):
                v.append({"x": a["x"], "lo": min(a["y"], b["y"]), "hi": max(a["y"], b["y"])})
        hs.append(h)
        vs.append(v)
    n = 0
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            for h, v in ((hs[i], vs[j]), (hs[j], vs[i])):
                for a in h:
                    for b in v:
                        if b["x"] > a["lo"] + m and b["x"] < a["hi"] - m and a["y"] > b["lo"] + m and a["y"] < b["hi"] - m:
                            n += 1
    return n


def crossings_with(path: list[dict], others: list[list[dict]], margin: float = 0, tol: float = 0) -> int:
    """lib/polyline-metrics.ts:69-71 crossingsWith(): the crossings of one polyline with each
    of the others (the same count as crossings_of, for a figure in which only this one changed)."""
    return crossings_of([path, *others], margin, tol) - crossings_of(list(others), margin, tol)


def score_of(paths: list[list[dict]]) -> dict:
    """lib/polyline-metrics.ts:74 scoreOf(): the candidate score of routed arrows (crossings
    and bends; lower is better, crossings compared first)."""
    return {"crossings": crossings_of(paths), "bends": sum(bends_of(p) for p in paths)}


def runs_together(a: dict, b: dict) -> bool:
    """lib/polyline-metrics.ts:77-82 runsTogether(): two runs of arrows side by side (under 4px
    apart, over 4px long together) — they read as one line. `a`/`b`: {p: Pt, q: Pt}."""
    ap, aq, bp, bq = a["p"], a["q"], b["p"], b["q"]
    a_h = ap["y"] == aq["y"]
    if a_h != (bp["y"] == bq["y"]):
        return False
    c, d = ("x", "y") if a_h else ("y", "x")
    if abs(ap[d] - bp[d]) >= 4:
        return False
    return min(max(ap[c], aq[c]), max(bp[c], bq[c])) - max(min(ap[c], aq[c]), min(bp[c], bq[c])) > 4
