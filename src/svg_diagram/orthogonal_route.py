"""1:1 port of lib/orthogonal-route.ts's routeClear() — an orthogonal route that keeps clear of
boxes, found by grid search (Dijkstra on the grid made by the boxes' inflated edges plus hint
lines). The last-resort router for bpmn() flows that a fixed list of shapes can't connect. Pure
geometry, no text/font dependency. Exported in Node and golden-tested live.

Golden master: lib/orthogonal-route.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .emit_common import js_round

_BEND, _CROSS, _RIDE = 30, 25, 150
_DX = [1, 0, -1, 0]
_DY = [0, 1, 0, -1]


def _ports(r: dict, stub: float) -> list[dict]:
    cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
    return [
        {"edge": {"x": r["x"] + r["w"], "y": cy}, "out": {"x": r["x"] + r["w"] + stub, "y": cy}, "dir": 0},
        {"edge": {"x": cx, "y": r["y"] + r["h"]}, "out": {"x": cx, "y": r["y"] + r["h"] + stub}, "dir": 1},
        {"edge": {"x": r["x"], "y": cy}, "out": {"x": r["x"] - stub, "y": cy}, "dir": 2},
        {"edge": {"x": cx, "y": r["y"]}, "out": {"x": cx, "y": r["y"] - stub}, "dir": 3},
    ]


def _snap(v: float) -> float:
    return js_round(v * 2) / 2


def route_clear(o: dict) -> list[dict] | None:
    """lib/orthogonal-route.ts:31-82 routeClear(). `o`: {from, to, boxes, bounds, others?, xs?,
    ys?, margin?, stub?} (all rects {x, y, w, h}; `others` a list of polylines [{x, y}, ...]).
    Returns the route's points (edge-to-edge), or None when the boxes close every way."""
    m, stub = o.get("margin", 6), o.get("stub", 14)
    b = o["bounds"]
    solid = [{"x": r["x"] - m, "y": r["y"] - m, "w": r["w"] + 2 * m, "h": r["h"] + 2 * m} for r in o["boxes"]]
    pa, pb = _ports(o["from"], stub), _ports(o["to"], stub)

    def inside(p: dict) -> bool:
        return any(r["x"] < p["x"] < r["x"] + r["w"] and r["y"] < p["y"] < r["y"] + r["h"] for r in solid)

    xset: set[float] = set()
    yset: set[float] = set()

    def add_x(v: float) -> None:
        if b["x"] <= v <= b["x"] + b["w"]:
            xset.add(_snap(v))

    def add_y(v: float) -> None:
        if b["y"] <= v <= b["y"] + b["h"]:
            yset.add(_snap(v))

    for r in solid:
        add_x(r["x"])
        add_x(r["x"] + r["w"])
        add_y(r["y"])
        add_y(r["y"] + r["h"])
    for p in [*pa, *pb]:
        add_x(p["out"]["x"])
        add_y(p["out"]["y"])
    for v in o.get("xs") or []:
        add_x(v)
    for v in o.get("ys") or []:
        add_y(v)
    add_x(b["x"] + 2)
    add_x(b["x"] + b["w"] - 2)
    add_y(b["y"] + 2)
    add_y(b["y"] + b["h"] - 2)
    xs, ys = sorted(xset), sorted(yset)
    nx, ny = len(xs), len(ys)
    xs_index = {v: i for i, v in enumerate(xs)}
    ys_index = {v: j for j, v in enumerate(ys)}

    def X(i: int) -> float:
        return xs[i] if 0 <= i < nx else 0

    def Y(j: int) -> float:
        return ys[j] if 0 <= j < ny else 0

    free = [not inside({"x": X(k % nx), "y": Y(k // nx)}) for k in range(nx * ny)]

    def step(i: int, j: int, d: int) -> float | None:
        i2, j2 = i + _DX[d], j + _DY[d]
        if i2 < 0 or j2 < 0 or i2 >= nx or j2 >= ny or not free[j2 * nx + i2]:
            return None
        x1, x2 = min(X(i), X(i2)), max(X(i), X(i2))
        y1, y2 = min(Y(j), Y(j2)), max(Y(j), Y(j2))
        horiz = d % 2 == 0
        for r in solid:
            if horiz:
                if r["y"] < y1 < r["y"] + r["h"] and x1 < r["x"] + r["w"] and x2 > r["x"]:
                    return None
            elif r["x"] < x1 < r["x"] + r["w"] and y1 < r["y"] + r["h"] and y2 > r["y"]:
                return None
        cost = x2 - x1 + y2 - y1
        for e in o.get("others") or []:
            for k in range(1, len(e)):
                p, q = e[k - 1], e[k]
                ph = p["y"] == q["y"]
                ex1, ex2 = min(p["x"], q["x"]), max(p["x"], q["x"])
                ey1, ey2 = min(p["y"], q["y"]), max(p["y"], q["y"])
                if ph == horiz:
                    coincide = p["y"] == y1 if horiz else p["x"] == x1
                    overlap = (min(x2, ex2) - max(x1, ex1)) if horiz else (min(y2, ey2) - max(y1, ey1))
                    if coincide and overlap > 0:
                        cost += _RIDE
                elif (x1 < ex1 < x2 and ey1 < y1 < ey2) if horiz else (y1 < ey1 < y2 and ex1 < x1 < ex2):
                    cost += _CROSS
        return cost

    def at(p: dict) -> tuple[int, int]:
        return xs_index.get(_snap(p["x"]), -1), ys_index.get(_snap(p["y"]), -1)

    def key(i: int, j: int, d: int) -> int:
        return (j * nx + i) * 4 + d

    dist: dict[int, float] = {}
    prev: dict[int, int] = {}
    src_port: dict[int, int] = {}
    queue: list[tuple[float, int]] = []
    for k, p in enumerate(pa):
        i, j = at(p["out"])
        if i < 0 or j < 0 or not free[j * nx + i]:
            continue
        kk = key(i, j, p["dir"])
        dist[kk] = 0
        src_port[kk] = k
        queue.append((0, kk))
    goal: dict[int, int] = {}
    for k, p in enumerate(pb):
        i, j = at(p["out"])
        if i >= 0 and j >= 0 and free[j * nx + i]:
            goal[j * nx + i] = k

    best: dict | None = None
    while queue:
        queue.sort(key=lambda e: -e[0])
        c, s = queue.pop()
        if c > dist.get(s, math.inf):
            continue
        if best is not None and c >= best["cost"]:
            break
        d = s % 4
        cell = s // 4
        i, j = cell % nx, cell // nx
        if cell in goal:
            side = pb[goal[cell]]
            tc = c + (0 if d == (side["dir"] + 2) % 4 else _BEND)
            if best is None or tc < best["cost"]:
                best = {"k": s, "cost": tc}
        for nd in range(4):
            if nd == (d + 2) % 4:
                continue
            w = step(i, j, nd)
            if w is None:
                continue
            k2 = key(i + _DX[nd], j + _DY[nd], nd)
            c2 = c + w + (0 if nd == d else _BEND)
            if c2 < dist.get(k2, math.inf):
                dist[k2] = c2
                prev[k2] = s
                queue.append((c2, k2))

    if best is None:
        return None
    path: list[dict] = []
    s: int | None = best["k"]
    first = s
    while s is not None:
        first = s
        cell = s // 4
        path.append({"x": X(cell % nx), "y": Y(cell // nx)})
        s = prev.get(s)
    path.reverse()
    end = pb[goal[best["k"] // 4]]
    assert first is not None  # s starts non-None (best["k"], checked above) and the loop always runs at least once
    start = pa[src_port[first]]
    return [start["edge"], *path, end["edge"]]
