"""Golden-master tests for layered_route.py's route_layered() against Node's routeLayered()
(lib/layered-route.ts, exported — live-tested via emit_cli.ts). route_layered() is the only
testable surface for the internal _route_once() (Node's non-exported routeOnce): each case
below is chosen to exercise one of its ADR 0016 passes (D3 straightening, D7 outer lanes,
D11 AND lane-sharing, D12/D13 aside, detour search), per the phased plan.

`place`/`groupOf`/`round` are callbacks that cannot cross the JSON-lines protocol: both this
test file and emit_cli.ts build matching closures from the same small serializable spec (see
emit_cli.ts's buildPlace/buildGroupOf/buildRound)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from svg_diagram.graph_layout import layout_layered
from svg_diagram.layered_route import route_layered


def _place_from_spec(spec: dict | None) -> Callable[[dict], dict]:
    spec = spec or {}
    swap, scale, dx, dy = spec.get("swap", False), spec.get("scale", 1), spec.get("dx", 0), spec.get("dy", 0)

    def place(p: dict) -> dict:
        return {"x": (p["y"] if swap else p["x"]) * scale + dx, "y": (p["x"] if swap else p["y"]) * scale + dy}

    return place


def _group_of_from_spec(spec: dict[int, int] | None) -> Callable[[int], int | None] | None:
    if not spec:
        return None
    m = dict(spec)
    return lambda edge: m.get(edge)


def _round_from_spec(ids: list[str] | None) -> Callable[[str], bool] | None:
    if not ids:
        return None
    s = set(ids)
    return lambda node_id: node_id in s


def _n(*specs: tuple[str, float, float]) -> list[dict]:
    """`specs`: (id, w, h)."""
    return [{"id": i, "size": {"w": w, "h": h}} for i, w, h in specs]


def _e(*pairs: tuple[str, str]) -> list[dict]:
    return [{"from": a, "to": b} for a, b in pairs]


IDENTITY_PLACE = {"swap": False, "scale": 1, "dx": 0, "dy": 0}

# 1. a 2-layer chain with 3 direct arrows sharing one gap (assignLanes/laneIn/forward/goesDown)
FAN = (_n(("a", 40, 20), ("b", 40, 20), ("c", 40, 20), ("d", 40, 20)), _e(("a", "c"), ("a", "d"), ("b", "c")))

# 2. a long arrow skipping a layer, grouped (AND) with a direct arrow into the same head
AND_GROUP = (_n(("a", 40, 20), ("b", 40, 20), ("head", 40, 20)), _e(("a", "b"), ("b", "head"), ("a", "head")))
AND_GROUP_OF = {2: 0, 1: 0}  # edge index 2 (a->head, long) and 1 (b->head, direct) share group 0

# 3. a cycle with a declared back edge, laid out with an outer lane
CYCLE_OUTER = (_n(("a", 40, 20), ("b", 40, 20), ("c", 40, 20)), _e(("a", "b"), ("b", "c"), ("c", "a")))

# 4. 3 ports fan into one box's side
FAN_IN_3 = (_n(("a", 40, 20), ("b", 40, 20), ("c", 40, 20), ("hub", 40, 60)), _e(("a", "hub"), ("b", "hub"), ("c", "hub")))

# 5. a padding sibling pushes "tall"/"short" off their natural centre-alignment, so D3's
# align() has real work to do (confirmed by hand: straighten=True actually straightens edge 0
# here, unlike the plain tall->short case where the base layout already centres them)
TALL_SHORT = (_n(("tall", 40, 120), ("pad", 40, 20), ("short", 40, 20)), _e(("tall", "short"), ("pad", "short")))

# 6. a tall blocking node shares the middle layer with "mid", so the long arrow a->b (which
# skips that layer) has to detour around it (confirmed by hand: detour=True gives edge 2
# strictly fewer bends than detour=False on this exact graph)
DETOUR_BLOCKED = (_n(("a", 40, 20), ("block", 40, 200), ("mid", 40, 20), ("b", 40, 20)), _e(("a", "mid"), ("mid", "b"), ("a", "b"), ("a", "block")))

# 7. one box side mixing a tail end (end=0) and a head end (end=1) of different edges, with groupOf set
MIXED_ENDS = (_n(("a", 40, 20), ("mid", 40, 20), ("head", 40, 20)), _e(("a", "mid"), ("mid", "head"), ("a", "head")))
MIXED_ENDS_GROUP_OF = {2: 0, 1: 0}

ROUTE_CASES: list[dict] = [
    {"id": "fan-shared-gap", "graph": FAN, "layout_opts": {}, "opts": {}},
    {"id": "and-group-long-arrow-shares-lane", "graph": AND_GROUP, "layout_opts": {}, "opts": {"groupOf": AND_GROUP_OF, "laneShare": True}},
    {"id": "and-group-no-share", "graph": AND_GROUP, "layout_opts": {}, "opts": {"groupOf": AND_GROUP_OF}},
    {"id": "cycle-outer-lane", "graph": CYCLE_OUTER, "layout_opts": {"back": [2], "outer": {"which": "all", "gap": 10, "step": 6}}, "opts": {}},
    {"id": "cycle-outer-lane-heads", "graph": CYCLE_OUTER, "layout_opts": {"back": [2], "outer": {"which": "all", "gap": 10, "step": 6}}, "opts": {"laneHeads": True}},
    {"id": "fan-in-3-ports", "graph": FAN_IN_3, "layout_opts": {}, "opts": {}},
    {"id": "tall-short-straighten", "graph": TALL_SHORT, "layout_opts": {}, "opts": {}},
    {"id": "tall-short-no-straighten", "graph": TALL_SHORT, "layout_opts": {}, "opts": {"straighten": False}},
    {"id": "detour-blocked", "graph": DETOUR_BLOCKED, "layout_opts": {}, "opts": {"detour": True}},
    {"id": "detour-blocked-no-detour", "graph": DETOUR_BLOCKED, "layout_opts": {}, "opts": {}},
    {"id": "mixed-ends-group-of", "graph": MIXED_ENDS, "layout_opts": {}, "opts": {"groupOf": MIXED_ENDS_GROUP_OF}},
    {"id": "mixed-ends-group-of-lane-share", "graph": MIXED_ENDS, "layout_opts": {}, "opts": {"groupOf": MIXED_ENDS_GROUP_OF, "laneShare": True}},
    {"id": "lone-ports-true-without-detour", "graph": FAN, "layout_opts": {}, "opts": {"lonePorts": True}},
    {"id": "space-compact", "graph": FAN, "layout_opts": {}, "opts": {"space": 0.75}},
    {"id": "aside-and-group", "graph": AND_GROUP, "layout_opts": {}, "opts": {"groupOf": AND_GROUP_OF, "aside": True}},
    {"id": "round-nodes-skip-straightening", "graph": TALL_SHORT, "layout_opts": {}, "opts": {"round": ["tall", "short"]}},
    {"id": "transposed-place", "graph": FAN, "layout_opts": {}, "opts": {"place": {"swap": True, "scale": 1, "dx": 5, "dy": 7}}},
    {"id": "port-step-custom", "graph": FAN_IN_3, "layout_opts": {}, "opts": {"portStep": 8}},
]


@pytest.mark.parametrize("case", ROUTE_CASES, ids=lambda c: c["id"])
def test_route_layered_matches_node(node_golden, case):
    nodes, edges = case["graph"]
    opts = case["opts"]
    req = {
        "kind": "routeLayered",
        "nodes": nodes,
        "edges": edges,
        "layoutOpts": case["layout_opts"],
        "place": opts.get("place", IDENTITY_PLACE),
        "portStep": opts.get("portStep", 14),
        "groupOf": opts.get("groupOf"),
        "round": opts.get("round"),
        "straighten": opts.get("straighten", True),
        "laneShare": opts.get("laneShare", False),
        "aside": opts.get("aside", False),
        "detour": opts.get("detour", False),
        "lonePorts": opts.get("lonePorts"),
        "space": opts.get("space", 1),
        "laneHeads": opts.get("laneHeads", False),
    }
    node_result = node_golden.call(req)

    lay = layout_layered(nodes, edges, case["layout_opts"])
    py_result = route_layered(
        lay,
        _place_from_spec(opts.get("place")),
        opts.get("portStep", 14),
        _group_of_from_spec(opts.get("groupOf")),
        _round_from_spec(opts.get("round")),
        opts.get("straighten", True),
        opts.get("laneShare", False),
        opts.get("aside", False),
        opts.get("detour", False),
        opts.get("lonePorts"),
        opts.get("space", 1),
        opts.get("laneHeads", False),
    )
    assert {str(k): v for k, v in py_result.items()} == node_result
