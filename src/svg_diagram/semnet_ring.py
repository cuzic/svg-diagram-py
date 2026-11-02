"""1:1 port of lib/semnet-ring.ts: causalLoop({layout: 'ring'}) — the nodes of one loop on an
ellipse, the loop's links as elliptic arcs (ADR 0011 D).

Golden master: lib/semnet-ring.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .charts_base import Canvas, seg_hits_rect
from .emit_common import js_round

RING_MIN, RING_MAX = 2, 8
_GAP = 36  # between neighbours: an arrow plus its sign


def _ring_fail(msg: str) -> None:
    raise ValueError(f"causalLoop({{layout: 'ring'}}): {msg}")


def check_ring(nodes: list[dict], links: list[dict], loops: list[dict], direction: object) -> None:
    """lib/semnet-ring.ts:14-23 checkRing(): what a ring needs — exactly one loop of 2-8
    nodes (self links aside) that every node is on, and no link besides the loop's own."""
    if direction is not None:
        _ring_fail("direction has no meaning on a ring (drop direction, or use layout: 'layered')")
    real = [l for l in loops if len(l["nodes"]) > 1]
    how = "use layout: 'layered'; a node outside the loop is an intervention"
    if len(real) != 1:
        _ring_fail(f"the graph must be one loop (found {len(real)} loops; {how})")
        return
    loop = real[0]
    on = set(loop["nodes"])
    out_node = next((n for n in nodes if n["id"] not in on), None)
    if out_node is not None:
        _ring_fail(f'the graph must be one loop ("{out_node["id"]}" is not on it; {how})')
    if len(loop["nodes"]) < RING_MIN or len(loop["nodes"]) > RING_MAX:
        _ring_fail(f"the loop has {len(loop['nodes'])} nodes; a ring takes {RING_MIN} to {RING_MAX} (use layout: 'layered')")
    own = set(loop["linkIndexes"])
    chord = next((l for i, l in enumerate(links) if i not in own and l["from"] != l["to"]), None)
    if chord is not None:
        _ring_fail(f"the link {chord['from']} -> {chord['to']} is not part of the loop (a ring has no chords; use layout: 'layered')")


def _gap_of(a: dict, b: dict) -> float:
    return max(a["x"] - (b["x"] + b["w"]), b["x"] - (a["x"] + a["w"]), a["y"] - (b["y"] + b["h"]), b["y"] - (a["y"] + a["h"]))


def _inside(r: dict, p: dict) -> bool:
    return r["x"] < p["x"] < r["x"] + r["w"] and r["y"] < p["y"] < r["y"] + r["h"]


def layout_ring(g: dict, ns: list[dict], loop: dict, self_links: list[dict], inset: dict | None = None) -> dict:
    """lib/semnet-ring.ts:29-67 layoutRing(): `loop.nodes` go clockwise from the top. rx
    follows from the width; ry is the first of 60, 68, ... where neighbours keep GAP between
    their boxes, no two boxes touch and no arc runs through a box that is not its end. The
    canvas is as high as that needs, unless `height` says more (and fails if it says less)."""
    inset = inset or {}
    self_loops = len(self_links) > 0
    n = len(loop["nodes"])
    by_id = {x["id"]: x for x in ns}
    order = [by_id[node_id] for node_id in loop["nodes"]]  # the nodes of a loop are nodes
    max_w = max(x["w"] for x in order)
    max_h = max(x["h"] for x in order)
    side_pad = 60 if self_loops else 0
    rx = (g["w"] - max_w - 16 - side_pad) / 2
    top_pad = 16 + (22 if self_loops else 0) + (inset.get("top") or 0)
    bot_pad = 16 + (22 if self_loops else 0) + (inset.get("bottom") or 0)
    if rx < 24:
        _ring_fail(f"the figure is too narrow for {n} nodes with these labels ({js_round(g['w'])}px wide; shorten the labels or use layout: 'layered')")
    step = 2 * math.pi / n

    def theta(i: int) -> float:
        return -math.pi / 2 + 2 * math.pi * i / n

    def at(ry: float, t: float) -> dict:
        return {"x": rx * math.cos(t), "y": ry * math.sin(t)}

    def boxes(ry: float) -> list[dict]:
        out = []
        for i, x in enumerate(order):
            p = at(ry, theta(i))
            out.append({"x": p["x"] - x["w"] / 2, "y": p["y"] - x["h"] / 2, "w": x["w"], "h": x["h"]})
        return out

    def arc(ry: float, bs: list[dict], i: int) -> list[dict]:
        """The arc from node i to node i+1, from where it leaves the first box to where it
        reaches the second."""
        a, b = bs[i], bs[(i + 1) % n]
        t0, t1 = theta(i), theta(i) + step
        lo, hi = t0, t1
        for _ in range(40):
            m = (lo + hi) / 2
            if _inside(a, at(ry, m)):
                lo = m
            else:
                hi = m
        frm = hi
        lo, hi = t0, t1
        for _ in range(40):
            m = (lo + hi) / 2
            if _inside(b, at(ry, m)):
                hi = m
            else:
                lo = m
        to = lo
        pts = [at(ry, frm)]
        cnt = max(0, math.ceil((to - frm) / (math.pi / 30)) - 1)
        for k in range(1, cnt + 1):
            pts.append(at(ry, frm + (to - frm) * k / (cnt + 1)))
        pts.append(at(ry, to))
        return pts

    ry = 60.0
    ok = False
    bs: list[dict] = []
    arcs: list[list[dict]] = []
    while ry <= 600:
        bs = boxes(ry)
        good = True
        for i in range(n):
            if not good:
                break
            for j in range(i + 1, n):
                if not good:
                    break
                needed = _GAP if (j - i == 1 or (i == 0 and j == n - 1)) else 8
                if _gap_of(bs[i], bs[j]) < needed:
                    good = False
        if good:
            arcs = [arc(ry, bs, i) for i in range(n)]
            for i in range(n):
                if not good:
                    break
                ai = arcs[i]
                for k in range(len(ai) - 1):
                    q, p = ai[k], ai[k + 1]
                    for j, r in enumerate(bs):
                        if j != i and j != (i + 1) % n and seg_hits_rect({"x1": q["x"], "y1": q["y"], "x2": p["x"], "y2": p["y"]}, r):
                            good = False
            if good and all(len(a) >= 2 and math.hypot(a[-1]["x"] - a[0]["x"], a[-1]["y"] - a[0]["y"]) >= 12 for a in arcs):
                ok = True
                break
        ry += 8
    if not ok:
        _ring_fail(f"the {n} nodes do not fit on a ring this wide ({js_round(g['w'])}px; shorten the labels, drop a node, or use layout: 'layered')")
    need = math.ceil(2 * ry + max_h + top_pad + bot_pad)
    if g.get("height") is not None and g["height"] < need:
        _ring_fail(f"height {g['height']} is too small for this ring; it needs at least {need} (raise height, or drop it to let the figure grow)")
    h = max(need, g.get("height") or 0)
    cx, cy = g["x"] + g["w"] / 2, g["y"] + top_pad + max_h / 2 + ry + (h - need) / 2

    def move(p: dict) -> dict:
        return {"x": cx + p["x"], "y": cy + p["y"]}

    c = Canvas(g["x"], g["y"], g["w"], h, g["size"], g["widthOf"], g["wrap"])
    positions: dict[str, dict] = {}
    for i, x in enumerate(order):
        r = bs[i]
        positions[x["id"]] = {"x": cx + r["x"], "y": cy + r["y"], "w": r["w"], "h": r["h"]}
    for x in order:
        p = positions[x["id"]]
        c.solids.append({**p, "id": x["id"], "label": f'node "{x["label"]}"'})
    paths: dict[int, list[dict]] = {}
    for i, li in enumerate(loop["linkIndexes"]):
        paths[li] = [move(p) for p in arcs[i]]
    # a link from a node to itself: a small loop on the side of the box that faces away from the middle (where no arc arrives)
    for sl in self_links:
        index, node_id = sl["index"], sl["node"]
        p = positions[node_id]
        dx = (p["x"] + p["w"] / 2 - cx) / rx
        dy = (p["y"] + p["h"] / 2 - cy) / ry
        ex, k = 22, 10
        if abs(dy) >= abs(dx):
            y = p["y"] if dy < 0 else p["y"] + p["h"]
            o = y - ex if dy < 0 else y + ex
            x = p["x"] + p["w"] / 2
            paths[index] = [{"x": x - k, "y": y}, {"x": x - k, "y": o}, {"x": x + k, "y": o}, {"x": x + k, "y": y}]
        else:
            x = p["x"] if dx < 0 else p["x"] + p["w"]
            o = x - ex if dx < 0 else x + ex
            y = p["y"] + p["h"] / 2
            paths[index] = [{"x": x, "y": y - k}, {"x": o, "y": y - k}, {"x": o, "y": y + k}, {"x": x, "y": y + k}]
    return {"c": c, "positions": positions, "paths": paths, "centre": {"x": cx, "y": cy}}
