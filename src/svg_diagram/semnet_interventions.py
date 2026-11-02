"""1:1 port of lib/semnet-interventions.ts: causalLoop({interventions}) — the boxes outside
the loop and the arrows from them (ADR 0011 C). Planning only decides where things go;
semnet_causal.py draws them (stage 1) and places their signs (stage 2).

Golden master: lib/semnet-interventions.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from collections.abc import Callable

from .charts_base import Canvas, seg_hits_rect
from .emit_common import js_round

BOX_H, ARROW, GAP, MARGIN = 48, 40, 16, 8


def band_inset(side: str, items: list[dict], attempt: int) -> float:
    """lib/semnet-interventions.ts:13 bandInset(): how much of the figure's `side` the band
    takes, `attempt` times 8px thicker each retry (the layout is given this much less room)."""
    if side == "left":
        return MARGIN + max([0.0, *(i["w"] for i in items)]) + ARROW + 8 * attempt
    return BOX_H + ARROW + 8 * attempt


def ring_side(loop_nodes: list[str], to: list[str]) -> str:
    """lib/semnet-interventions.ts:15-18 ringSide(): on a ring, a node in the upper half of
    the ellipse (the top included) is reached from above, the others from below."""
    upper = 0
    for node_id in to:
        f = loop_nodes.index(node_id) / len(loop_nodes)
        if f <= 0.25 + 1e-9 or f >= 0.75 - 1e-9:
            upper += 1
    return "top" if upper * 2 >= len(to) else "bottom"


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def _dedupe(values: list[float]) -> list[float]:
    """Matches a JS `new Set([...])`'s iteration order: first occurrence, in insertion order."""
    seen: list[float] = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen


def plan_interventions(c: Canvas, items: list[dict], positions: dict[str, dict], side_of: Callable[[dict], str]) -> dict:
    """lib/semnet-interventions.ts:25-70 planInterventions(): boxes in order of where their
    targets are, pushed apart by GAP (forwards, then back from the end), each with one arrow
    per target: straight when the box and the target share a stretch, otherwise down, across
    and down. An arrow may cross a loop link but not a node box. Returns {"placed": [...]}
    or {"problem": str}."""
    placed: list[dict] = []
    nodes = list(positions.items())
    boxes: list[dict] = []
    for side in ("top", "bottom", "left"):
        group = [i for i in items if side_of(i) == side]
        if not group:
            continue
        horizontal = side != "left"

        def length(i: dict, horizontal: bool = horizontal) -> float:
            return i["w"] if horizontal else BOX_H

        def centre_u(r: dict, horizontal: bool = horizontal) -> float:
            return r["x"] + r["w"] / 2 if horizontal else r["y"] + r["h"] / 2

        want = {i["id"]: sum(centre_u(positions[t]) for t in i["to"]) / len(i["to"]) for i in group}
        order = sorted(group, key=lambda i: (want[i["id"]], i["id"]))
        lo = (c.x if horizontal else c.y) + MARGIN
        start: dict[str, float] = {}
        prev = lo - GAP
        for i in order:
            s = max(want[i["id"]] - length(i) / 2, prev + GAP)
            start[i["id"]] = s
            prev = s + length(i)
        if horizontal:
            hi = c.x + c.w - MARGIN
            nxt = hi + GAP
            for i in reversed(order):
                s = min(start[i["id"]], nxt - GAP - length(i))
                start[i["id"]] = s
                nxt = s
            if nxt < lo - 1e-6:
                labels = ", ".join(f'"{i["label"]}"' for i in group)
                return {"problem": f"the {len(group)} intervention boxes on the {side} ({labels}) are wider than the figure ({js_round(c.w)}px)"}
        elif prev + MARGIN > c.y + c.h:  # a column of boxes may be taller than the loop; the figure grows
            c.h = prev + MARGIN - c.y
        for i in order:
            s = start[i["id"]]
            if side == "left":
                r = {"x": c.x + MARGIN, "y": s, "w": i["w"], "h": BOX_H}
            else:
                r = {"x": s, "y": (c.y + MARGIN if side == "top" else c.y + c.h - MARGIN - BOX_H), "w": i["w"], "h": BOX_H}
            boxes.append({"id": i["id"], "r": r})
        # arrows, once the boxes of this side are known
        for k, i in enumerate(order):
            r = next(b["r"] for b in boxes if b["id"] == i["id"])
            bt = r["w"] if side == "left" else r["h"]
            e = MARGIN + bt
            bu0 = r["x"] if horizontal else r["y"]
            bu1 = bu0 + length(i)

            def uv(q: dict, horizontal: bool = horizontal, side: str = side) -> dict:
                if horizontal:
                    return {"u0": q["x"], "u1": q["x"] + q["w"], "v0": (q["y"] - c.y) if side == "top" else (c.y + c.h - (q["y"] + q["h"]))}
                return {"u0": q["y"], "u1": q["y"] + q["h"], "v0": q["x"] - c.x}

            def xy(u: float, v: float, side: str = side) -> dict:
                if side == "left":
                    return {"x": c.x + v, "y": u}
                if side == "top":
                    return {"x": u, "y": c.y + v}
                return {"x": u, "y": c.y + c.h - v}

            arrows: list[dict] = []
            for to in i["to"]:
                t = uv(positions[to])
                n = t["v0"]
                m = e + 14 + 6 * (k % 4)
                tc = (t["u0"] + t["u1"]) / 2
                if n - e < 12 or m > n - 8:
                    return {"problem": f'the arrow of intervention "{i["id"]}" to "{to}" has no room between its box and the node'}
                lo2, hi2 = max(bu0 + 10, t["u0"] + 6), min(bu1 - 10, t["u1"] - 6)
                cands: list[list[tuple[float, float]]] = []
                if lo2 <= hi2:
                    for u in _dedupe([_clamp(tc, lo2, hi2), (lo2 + hi2) / 2, lo2, hi2]):
                        cands.append([(u, e), (u, n)])
                s0 = _clamp(tc, bu0 + 10, bu1 - 10)
                for en in _dedupe([_clamp(tc, t["u0"] + 6, t["u1"] - 6), t["u0"] + 8, t["u1"] - 8]):
                    cands.append([(s0, e), (s0, m), (en, m), (en, n)])
                hit_name = ""
                ok_path: list[dict] | None = None
                for cd in cands:
                    path = [xy(u, v) for u, v in cd]
                    blocked = False
                    for q in range(1, len(path)):
                        p0, p1 = path[q - 1], path[q]
                        sg = {"x1": p0["x"], "y1": p0["y"], "x2": p1["x"], "y2": p1["y"]}
                        hit = next((nid for nid, nr in nodes if nid != to and seg_hits_rect(sg, nr)), None)
                        if hit is None:
                            hit = next((b["id"] for b in boxes if b["id"] != i["id"] and seg_hits_rect(sg, b["r"])), None)
                        if hit:
                            if not hit_name:
                                hit_name = hit
                            blocked = True
                            break
                    if not blocked:
                        ok_path = path
                        break
                if ok_path is None:
                    return {"problem": f'the arrow of intervention "{i["id"]}" to "{to}" would run through "{hit_name or "a box"}"'}
                arrows.append({"to": to, "path": ok_path})
            placed.append({"item": i, "box": r, "arrows": arrows})
    off = next((p for p in placed if p["box"]["x"] < c.x - 0.5 or p["box"]["x"] + p["box"]["w"] > c.x + c.w + 0.5 or p["box"]["y"] < c.y - 0.5 or p["box"]["y"] + p["box"]["h"] > c.y + c.h + 0.5), None)
    if off is not None:
        return {"problem": f'the intervention "{off["item"]["id"]}" does not fit in the figure'}
    return {"placed": placed}
