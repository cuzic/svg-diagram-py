"""1:1 port of lib/layered-route.ts — orthogonal routing of the edges of a layered layout
(graph_layout.py's layout_layered()), shared by states()/classes()/cause()/pert()/
causalLoop()/dependencyNetwork() (none of those bands are wired to this module yet — see
BANDS.md's Tier 3 note; this port is the engine only).

Everything here is in the layout's own ('right') axes: layers run along x. `place` moves a
point of those axes into the figure (and transposes it for a 'down' diagram).

Depends on already-ported graph_layout.layout_layered(), polyline_metrics.py (simplify/
bends_of/crossings_of/crossings_with/score_of/runs_together), route_apart.move_apart(),
route_search.{head_crossings, search_route}.

Golden master: lib/layered-route.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .emit_common import js_round
from .graph_layout import layout_layered
from .polyline_metrics import simplify

STUB = 18
LANE = 14


def stub_of(space: float = 1) -> float:
    """lib/layered-route.ts:19 stubOf()."""
    return js_round(STUB * space)


def lane_step_of(space: float = 1) -> float:
    """lib/layered-route.ts:20 laneStepOf()."""
    return js_round(LANE * space)


def gap_for(n: int, chip: float = 0, space: float = 1) -> float:
    """lib/layered-route.ts:18 gapFor(): the gap two layers need so that `n` direct arrows
    through it each get a lane (and a label chip beside them has room)."""
    return max(2 * stub_of(space) + lane_step_of(space) * max(0, n - 1) + js_round(16 * space), chip + stub_of(space) + 26)


def elbows(pts: list[dict], turn: float | None = None, last_turn: float | None = None) -> list[dict]:
    """lib/layered-route.ts:27-38 elbows(): horizontal-vertical-horizontal elbows through the
    points (the layer axis is x here). A direct arrow turns at `turn` (an x in the gap between
    its two layers); the others turn half-way between their points."""
    out: list[dict] = pts[:1]
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        if p["y"] != q["y"]:
            if len(pts) == 2 and turn is not None:
                mx = turn
            elif i + 2 == len(pts) and last_turn is not None:
                mx = last_turn
            else:
                mx = (p["x"] + q["x"]) / 2
            out.append({"x": mx, "y": p["y"]})
            out.append({"x": mx, "y": q["y"]})
        out.append(q)
    return simplify(out)


def corridor_load(lay: dict) -> int:
    """lib/layered-route.ts:409-426 corridorLoad(): the most direct arrows that pass through
    one gap between two layers (each needs its own lane there)."""
    load: dict[str, int] = {}
    for e in lay["edges"]:
        if e.get("self") or len(e["points"]) != 2:
            continue
        a, b = lay["nodes"][e["from"]], lay["nodes"][e["to"]]
        k = f"{js_round(min(a['x'] + a['w'] / 2, b['x'] + b['w'] / 2))}:{js_round(max(a['x'] + a['w'] / 2, b['x'] + b['w'] / 2))}"
        load[k] = load.get(k, 0) + 1
    direct: dict[int, int] = {}
    outer_in: dict[int, int] = {}
    for e in lay["edges"]:
        if e.get("self"):
            continue
        l1, l2 = lay["layers"][e["from"]], lay["layers"][e["to"]]
        if e.get("outer"):
            for g in (l1 - 1, l2):
                outer_in[g] = outer_in.get(g, 0) + 1
        elif len(e["points"]) == 2:
            lo = min(l1, l2)
            direct[lo] = direct.get(lo, 0) + 1
    candidates = [1, *load.values(), *(n + direct.get(g, 0) for g, n in outer_in.items())]
    return max(candidates)


def layout_with_lanes(nodes: list[dict], edges: list[dict], opts: dict, chip: float = 0, space: float = 1) -> dict:
    """lib/layered-route.ts:432-436 layoutWithLanes(): layout_layered, with the gap between
    layers wide enough for the arrows that share it: laid out once to see how many arrows go
    through each gap (layers do not depend on the gap), then again with a gap that gives each
    its own lane."""
    first = layout_layered(nodes, edges, opts)
    need = gap_for(corridor_load(first), chip, space)
    return layout_layered(nodes, edges, {**opts, "levelGap": need}) if need > opts.get("levelGap", 0) else first
