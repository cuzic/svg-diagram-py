"""1:1 port of lib/route-apart.ts's moveApart() (exported, golden-tested live): long arrows
that run side by side (ADR 0016 D14) read as one line, so this moves one run of one arrow
across, a few px at a time, keeping a move only when it leaves the arrow beside fewer others
and makes nothing worse (crossings, bends, a pierced box, leaving the figure, a run too
short). Pure: placed routes in, placed routes out. Depends only on polyline_metrics.py
(already ported).

Golden master: lib/route-apart.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .emit_common import _sign
from .polyline_metrics import bends_of, crossings_with, runs_together

CLEAR = 6
JOG = 10
STEPS = [8, -8, 16, -16, 24, -24]


def _related(a: dict, b: dict) -> bool:
    return a["from"] == b["from"] or a["to"] == b["to"]


def move_apart(routes: dict[int, list[dict]], edges: dict[int, dict], rects: dict[str, dict]) -> dict[int, list[dict]]:
    """lib/route-apart.ts:26-102 moveApart(). `routes`: {edge index: [{x,y}, ...]}. `edges`:
    {edge index: {from, to, self?, outer?}}. `rects`: {node id: {x0, x1, y0, y1}}."""
    out: dict[int, list[dict]] = dict(routes)
    cache: dict[int, list[dict]] = {}

    def segs(r: list[dict]) -> list[dict]:
        key = id(r)
        s = cache.get(key)
        if s is None:
            s = [{"p": r[k - 1], "q": r[k]} for k in range(1, len(r))]
            cache[key] = s
        return s

    def movable(i: int) -> bool:
        e = edges.get(i)
        return e is not None and not e.get("self") and not e.get("outer")

    def beside(i: int, r: list[dict]) -> list[int]:
        ei = edges.get(i)
        if ei is None:
            return []
        mine = segs(r)
        return [j for j, o in out.items() if j != i and movable(j) and not _related(ei, edges[j]) and any(runs_together(x, y) for y in segs(o) for x in mine)]

    def near(i: int, r: list[dict]) -> set[int]:
        mine = segs(r)
        return {j for j, o in out.items() if j != i and any(runs_together(x, y) for y in segs(o) for x in mine)}

    def pierces(i: int, r: list[dict]) -> int:
        e = edges[i]
        n = 0
        for node_id, b in rects.items():
            if node_id == e["from"] or node_id == e["to"]:
                continue
            for seg in segs(r):
                p, q = seg["p"], seg["q"]
                if min(p["x"], q["x"]) < b["x1"] + CLEAR and max(p["x"], q["x"]) > b["x0"] - CLEAR and min(p["y"], q["y"]) < b["y1"] + CLEAR and max(p["y"], q["y"]) > b["y0"] - CLEAR:
                    n += 1
                    break
        return n

    def crowds(i: int, r: list[dict], t: list[dict], frm: int, to: int) -> bool:
        e = edges[i]

        def gap(route: list[dict], b: dict) -> float:
            g = math.inf
            for m in range(frm, to + 1):
                if m + 1 >= len(route):
                    continue
                p, q = route[m], route[m + 1]
                dx = max(b["x0"] - max(p["x"], q["x"]), min(p["x"], q["x"]) - b["x1"], 0)
                dy = max(b["y0"] - max(p["y"], q["y"]), min(p["y"], q["y"]) - b["y1"], 0)
                g = min(g, math.hypot(dx, dy))
            return g

        for node_id, b in rects.items():
            if node_id == e["from"] or node_id == e["to"]:
                continue
            after = gap(t, b)
            if after < CLEAR and after < gap(r, b):
                return True
        return False

    all_pts = [p for r in routes.values() for p in r]
    lo = {"x": min([p["x"] for p in all_pts] + [b["x0"] for b in rects.values()]), "y": min([p["y"] for p in all_pts] + [b["y0"] for b in rects.values()])}
    hi = {"x": max([p["x"] for p in all_pts] + [b["x1"] for b in rects.values()]), "y": max([p["y"] for p in all_pts] + [b["y1"] for b in rects.values()])}

    def inside(r: list[dict]) -> bool:
        return all(lo["x"] <= p["x"] <= hi["x"] and lo["y"] <= p["y"] <= hi["y"] for p in r)

    for _round in range(3):
        moved = False
        for i in list(out.keys()):
            if not movable(i):
                continue
            r = out.get(i)
            if r is None or len(r) < 4:
                continue
            now = beside(i, r)
            if not now:
                continue
            rest = [p for j, p in out.items() if j != i]
            base_x, base_p, base_n = crossings_with(r, rest), pierces(i, r), near(i, r)
            done = False
            # an inner run only: the first and the last stay on their ports; each is tried across, the smallest step first
            for k in range(1, len(r) - 2):
                if done:
                    break
                pk, qk = r[k], r[k + 1]
                vertical = pk["x"] == qk["x"]
                if not vertical and pk["y"] != qk["y"]:
                    continue
                s = {"p": pk, "q": qk}
                if not any(runs_together(s, y) for j in now for y in segs(out.get(j, []))):
                    continue
                for d in STEPS:
                    t = [dict(p) for p in r]
                    for m in (k, k + 1):
                        if vertical:
                            t[m]["x"] += d
                        else:
                            t[m]["y"] += d
                    c = "x" if vertical else "y"

                    def keeps(m: int, min_len: float) -> bool:
                        assert r is not None  # this closure only runs within the "if r is None: continue"-guarded loop body
                        r0, r1, t0, t1 = r[m], r[m + 1], t[m], t[m + 1]
                        before, after = r1[c] - r0[c], t1[c] - t0[c]
                        return before == 0 or (_sign(before) == _sign(after) and abs(after) >= min_len)

                    if not keeps(k - 1, JOG) or not keeps(k + 1, 22 if k + 2 == len(r) - 1 else JOG):
                        continue
                    if not inside(t) or pierces(i, t) > base_p or bends_of(t) > bends_of(r) or any(j not in base_n for j in near(i, t)) or crossings_with(t, rest) > base_x:
                        continue
                    # the moved run and its neighbours may not come nearer to a box than CLEAR unless they were that near before
                    if crowds(i, r, t, k - 1, k + 1):
                        continue
                    if len(beside(i, t)) >= len(now):
                        continue
                    out[i] = t
                    done = moved = True
                    break
        if not moved:
            break
    return out
