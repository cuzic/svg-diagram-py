"""1:1 port of lib/route-search.ts's headCrossings()/searchRoute() (both exported, golden-
tested live): the way around the boxes with the fewest bends, for one long arrow of a
layered layout (layered-route.ts, not yet ported). Pure geometry in the layout's own axes
(layers run along x) — an A* search over the grid of lines that run beside the boxes.
Depends only on a handful of free-standing helpers (no other unported module).

Golden master: lib/route-search.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .emit_common import js_round

HEAD_REACH = 22
_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def head_crossings(paths: list[list[dict]]) -> int:
    """lib/route-search.ts:28-45 headCrossings(): the crossings of a run across the layers
    with the last run of another arrow, within HEAD_REACH of its tip (they read as joins)."""
    n = 0
    for i, p in enumerate(paths):
        if len(p) < 2:
            continue
        tip, frm = p[-1], p[-2]
        if tip["y"] != frm["y"]:  # an arrow comes into a box along the layers (the layout's axes)
            continue
        for j, q in enumerate(paths):
            if j == i:
                continue
            for k in range(1, len(q)):
                a, b = q[k - 1], q[k]
                if a["x"] != b["x"]:  # a run across the layers
                    continue
                if a["x"] < min(frm["x"], tip["x"]) - 0.5 or a["x"] > max(frm["x"], tip["x"]) + 0.5 or abs(a["x"] - tip["x"]) > HEAD_REACH:
                    continue
                if tip["y"] > min(a["y"], b["y"]) + 0.5 and tip["y"] < max(a["y"], b["y"]) - 0.5:
                    n += 1
    return n


def search_route(
    start: dict,
    end: dict,
    boxes: list[dict],
    others: list[list[dict]],
    bounds: dict,
    *,
    margin: float = 8,
    stub: float = 18,
    tail: float = 26,
    bend: float = 30,
    cross: float = 25,
    along: float = 200,
    head: float = 300,
    budget: int = 60000,
) -> list[dict] | None:
    """lib/route-search.ts:53-140 searchRoute(): a polyline from `start` to `end` (both on box
    sides; the arrow runs toward larger x) that keeps `margin` off every box in `boxes`, stays
    in `bounds`, and costs least in length, bends, crossings of `others` and runs along them.
    None when there is none."""
    m, bend_c, cross_c, along_c, head_c = margin, bend, cross, along, head

    def r2(v: float) -> float:
        return js_round(v * 64) / 64

    s = {"x": r2(start["x"] + stub), "y": start["y"]}
    g = {"x": r2(end["x"] - tail), "y": end["y"]}
    if g["x"] < s["x"]:
        return None
    xs = {s["x"], g["x"]}
    ys = {s["y"], g["y"], r2(bounds["y"] + m), r2(bounds["y"] + bounds["h"] - m)}
    for b in boxes:
        xs.add(r2(b["x"] - m))
        xs.add(r2(b["x"] + b["w"] + m))
        ys.add(r2(b["y"] - m))
        ys.add(r2(b["y"] + b["h"] + m))
    X = sorted(x for x in xs if s["x"] - 0.01 <= x <= g["x"] + 0.01 and bounds["x"] <= x <= bounds["x"] + bounds["w"])
    Y = sorted(y for y in ys if bounds["y"] <= y <= bounds["y"] + bounds["h"])
    xi = {x: i for i, x in enumerate(X)}
    yi = {y: j for j, y in enumerate(Y)}
    if s["x"] not in xi or s["y"] not in yi or g["x"] not in xi or g["y"] not in yi:
        return None
    nx, ny = len(X), len(Y)

    def in_box(x: float, y: float) -> bool:
        return any(b["x"] - m + 0.01 < x < b["x"] + b["w"] + m - 0.01 and b["y"] - m + 0.01 < y < b["y"] + b["h"] + m - 0.01 for b in boxes)

    blocked_pt = [0] * (nx * ny)
    blocked_right = [0] * (nx * ny)
    blocked_down = [0] * (nx * ny)
    for j in range(ny):
        for i in range(nx):
            xv, yv = X[i], Y[j]
            blocked_pt[j * nx + i] = 1 if in_box(xv, yv) else 0
            if i + 1 < nx:
                blocked_right[j * nx + i] = 1 if in_box((xv + X[i + 1]) / 2, yv) else 0
            if j + 1 < ny:
                blocked_down[j * nx + i] = 1 if in_box(xv, (yv + Y[j + 1]) / 2) else 0

    def step_blocked(i: int, j: int, nd: int) -> bool:
        if nd == 0:
            return blocked_right[j * nx + i] == 1
        if nd == 1:
            return blocked_right[j * nx + i - 1] == 1
        if nd == 2:
            return blocked_down[j * nx + i] == 1
        return blocked_down[(j - 1) * nx + i] == 1

    hor: list[tuple[dict, dict]] = []
    ver: list[tuple[dict, dict]] = []
    tips: list[dict] = []
    for p in others:
        for k in range(1, len(p)):
            a, b = p[k - 1], p[k]
            (hor if b["y"] == a["y"] else ver).append((a, b))
        if len(p) >= 2:
            tip, before = p[-1], p[-2]
            if tip["y"] == before["y"]:
                tips.append(tip)

    def step_cost(a: dict, b: dict) -> float:
        c = abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])
        h = a["y"] == b["y"]
        along_list = hor if h else ver
        across_list = ver if h else hor
        t0, t1 = (a["x"], b["x"]) if h else (a["y"], b["y"])
        lo, hi = min(t0, t1), max(t0, t1)
        up = t1 > t0
        fixed = a["y"] if h else a["x"]
        u, v = ("x", "y") if h else ("y", "x")
        for p, q in along_list:  # the same line (within 4px), overlapping
            if abs(p[v] - fixed) < 4 and min(hi, max(p[u], q[u])) - max(lo, min(p[u], q[u])) > 1:
                c += along_c
        for p, q in across_list:  # a crossing: strictly inside the other run, and in this step (the far end counts, the near end does not)
            pos = p["x"] if h else p["y"]
            f0 = min(p["y"], q["y"]) if h else min(p["x"], q["x"])
            f1 = max(p["y"], q["y"]) if h else max(p["x"], q["x"])
            if not (fixed > f0 + 0.5 and fixed < f1 - 0.5):
                continue
            inside = (pos > lo + 0.01 and pos <= hi + 0.01) if up else (pos >= lo - 0.01 and pos < hi - 0.01)
            if inside:
                c += cross_c
        if not h:
            for t in tips:
                if abs(fixed - t["x"]) <= HEAD_REACH and t["y"] > lo + 0.01 and t["y"] < hi - 0.01:
                    c += head_c
        return c

    def key(i: int, j: int, d: int) -> int:
        return (j * nx + i) * 4 + d

    dist = [math.inf] * (nx * ny * 4)
    prev = [-1] * (nx * ny * 4)
    cached = [-1.0] * (nx * ny * 4)
    i0, j0 = xi[s["x"]], yi[s["y"]]
    ig, jg = xi[g["x"]], yi[g["y"]]
    xg, yg = X[ig], Y[jg]

    def left(i: int, j: int) -> float:
        return abs(xg - X[i]) + abs(yg - Y[j])

    heap: list[tuple[float, int]] = []

    def push(c: float, k: int) -> None:
        heap.append((c, k))
        i = len(heap) - 1
        while i > 0:
            p = (i - 1) >> 1
            if heap[p][0] <= heap[i][0]:
                break
            heap[p], heap[i] = heap[i], heap[p]
            i = p

    def pop() -> tuple[float, int]:
        top = heap[0]
        last = heap.pop()
        if heap:
            heap[0] = last
            i = 0
            while True:
                left_i, right_i = 2 * i + 1, 2 * i + 2
                mi = i
                if left_i < len(heap) and heap[left_i][0] < heap[mi][0]:
                    mi = left_i
                if right_i < len(heap) and heap[right_i][0] < heap[mi][0]:
                    mi = right_i
                if mi == i:
                    break
                heap[mi], heap[i] = heap[i], heap[mi]
                i = mi
        return top

    k0 = key(i0, j0, 0)
    dist[k0] = step_cost(start, s)
    push(dist[k0] + left(i0, j0), k0)
    finish = step_cost(g, end)
    goal, best_total, steps, over = -1, math.inf, 0, False
    while heap:
        f, k = pop()
        d = k % 4
        cell = (k - d) // 4
        i, j = cell % nx, (cell - cell % nx) // nx
        c = dist[k]
        if f > c + left(i, j) + 1e-9:  # stale
            continue
        if f + finish >= best_total:  # every way ends with the last run
            break
        if i == ig and j == jg:
            total = c + (0 if d == 0 else bend_c) + finish
            if total < best_total:
                best_total = total
                goal = k
        for nd in range(4):
            if nd == (d ^ 1):  # no turning back
                continue
            dx, dy = _DIRS[nd]
            ni, nj = i + dx, j + dy
            if ni < 0 or nj < 0 or ni >= nx or nj >= ny:
                continue
            steps += 1
            if steps > budget:  # over the budget: the way found so far (not proved the best), or none
                if goal < 0:
                    return None
                over = True
                break
            if blocked_pt[nj * nx + ni] or step_blocked(i, j, nd):
                continue
            ck = key(i, j, nd)
            sc = cached[ck]
            if sc < 0:
                sc = step_cost({"x": X[i], "y": Y[j]}, {"x": X[ni], "y": Y[nj]})
                cached[ck] = sc
            nc = c + sc + (0 if nd == d else bend_c)
            nk = key(ni, nj, nd)
            if nc < dist[nk]:
                dist[nk] = nc
                prev[nk] = k
                push(nc + left(ni, nj), nk)
        if over:
            break
    if goal < 0:
        return None
    pts: list[dict] = []
    k = goal
    while k >= 0:
        d = k % 4
        cell = (k - d) // 4
        i = cell % nx
        pts.append({"x": X[i], "y": Y[(cell - i) // nx]})
        k = prev[k]
    pts.reverse()
    return [start, *pts, end]
