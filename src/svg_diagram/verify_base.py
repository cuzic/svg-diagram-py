"""Scoped port of lib/verify-base.ts — only statesProblems() and the geometry helpers it
needs (rectOverlap/segBox/routeHits/routesThroughNodes/outsideX/dxdy). The rest of
lib/verify-base.ts backs the `check` CLI tool's per-band-type checks (verify-handlers.ts),
which is out of this port's scope — but statesProblems() itself is NOT just a check-tool
helper: layout_states_band()'s `density: 'compact'` fallback (ADR 0036 D6) calls it directly
to decide whether the compact layout is actually drawable, so it must be ported for
layout correctness, not just diagnostics.

Golden master: lib/verify-base.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .emit_common import js_round
from .states_words import states_words


def rect_overlap(a: dict, b: dict, tolerance: float = 0.5) -> dict | None:
    """lib/verify-base.ts:13-17 rectOverlap(): the overlap {dx,dy} if two rects share more
    than `tolerance`px of area in both axes, else None."""
    ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    if ox <= tolerance or oy <= tolerance:
        return None
    return {"dx": ox, "dy": oy}


def seg_box(p: dict, q: dict) -> dict:
    """lib/verify-base.ts:28 segBox(): the 1px-padded box of one straight run of a route."""
    return {"x": min(p["x"], q["x"]) - 1, "y": min(p["y"], q["y"]) - 1, "w": abs(p["x"] - q["x"]) + 2, "h": abs(p["y"] - q["y"]) + 2}


def route_hits(points: list[dict], r: dict) -> bool:
    """lib/verify-base.ts:30 routeHits(): does any run of the route touch `r`?"""
    return any(rect_overlap(r, seg_box(points[m], q)) is not None for m, q in enumerate(points[1:]))


def routes_through_nodes(edges: list[dict], nodes: list[dict], say) -> list[str]:
    """lib/verify-base.ts:32-44 routesThroughNodes(): for each route and each node it does not
    start or end at, the first run that touches the node reports once (`say(e, n)`)."""
    problems: list[str] = []
    for e in edges:
        for n in nodes:
            if n["id"] == e["from"] or n["id"] == e["to"]:
                continue
            pts = e["points"]
            for i in range(len(pts) - 1):
                if rect_overlap(seg_box(pts[i], pts[i + 1]), n) is not None:
                    problems.append(say(e, n))
                    break
    return problems


def dxdy(o: dict) -> str:
    """lib/verify-base.ts:52 dxdy()."""
    return f"{js_round(o['dx'])}x{js_round(o['dy'])}px"


def outside_x(r: dict, fig: dict) -> bool:
    """lib/verify-base.ts:54 outsideX(): past the left or right edge of the figure."""
    return r["x"] < fig["x"] - 0.5 or r["x"] + r["w"] > fig["x"] + fig["w"] + 0.5


def states_problems(band: dict) -> list[str]:
    """lib/verify-base.ts:62-78 statesProblems(): what the check finds wrong in a laid-out
    state diagram: a transition through a state it does not touch, a label chip outside the
    figure, on a state, on another arrow or on another chip. The check (verify-handlers.ts,
    out of this port's scope) and the layout (layout_states_band(): `density: 'compact'`
    falls back to the normal gaps when this finds more) use the same list."""
    w = states_words(band.get("flavor"))
    problems = routes_through_nodes(
        band["edges"], band["anchors"], lambda e, n: f"{w['prefix']}: {w['edge']} {e['from']} -> {e['to']} runs through {w['node']} \"{n['id']}\" (reorder the {w['node']}s, or change dir)"
    )
    labels = band["labels"]
    for i, l in enumerate(labels):
        if outside_x(l, band):
            problems.append(f"{w['prefix']}: label \"{l['text']}\" runs outside the figure (shorten it or widen the figure)")
        for n in band["anchors"]:
            if rect_overlap(l, n) is not None:
                problems.append(f"{w['prefix']}: label \"{l['text']}\" overlaps {w['node']} \"{n['id']}\" (shorten the label)")
        for k, e in enumerate(band["edges"]):  # the chip is white: on another arrow it would cut it
            if k != l["edge"] and route_hits(e["points"], l):
                problems.append(f"{w['prefix']}: label \"{l['text']}\" sits on the arrow {e['from']} -> {e['to']} (it belongs to another arrow)")
        for j in range(i + 1, len(labels)):
            other = labels[j]
            o = rect_overlap(l, other)
            if o is not None:
                problems.append(f"{w['prefix']}: label \"{l['text']}\" overlaps label \"{other['text']}\" by {dxdy(o)}")
    return problems
