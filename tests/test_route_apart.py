"""Golden-master tests for route_apart.py's move_apart() against Node's moveApart()
(lib/route-apart.ts, exported — live-tested via emit_cli.ts). Depends only on
polyline_metrics.py (already ported, also golden-tested)."""

from __future__ import annotations

import pytest

from svg_diagram.route_apart import move_apart


def _p(x: float, y: float) -> dict:
    return {"x": x, "y": y}


def _rect(x0: float, y0: float, x1: float, y1: float) -> dict:
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1}


# two arrows whose vertical runs through the same gap (x=50) overlap for 80px: they read as one line
PARALLEL_ROUTES = {
    0: [_p(10, 0), _p(50, 0), _p(50, 100), _p(90, 100)],
    1: [_p(10, 20), _p(50, 20), _p(50, 120), _p(90, 120)],
}
PARALLEL_EDGES = {0: {"from": "A", "to": "C"}, 1: {"from": "B", "to": "D"}}
PARALLEL_RECTS = {
    "A": _rect(0, -10, 10, 10), "B": _rect(0, 10, 10, 30),
    "C": _rect(90, 90, 100, 110), "D": _rect(90, 110, 100, 130),
}

# the same shape, but one edge is a self-loop (never moved) and the other 'outer' (never moved)
NOT_MOVABLE_EDGES = {0: {"from": "A", "to": "C", "self": True}, 1: {"from": "B", "to": "D", "outer": True}}

# two short routes, far apart: nothing is "beside" anything, so nothing can move
FAR_APART_ROUTES = {
    0: [_p(0, 0), _p(20, 0), _p(20, 20), _p(40, 20)],
    1: [_p(0, 200), _p(20, 200), _p(20, 220), _p(40, 220)],
}
FAR_APART_RECTS = {"A": _rect(-10, -10, 0, 10), "B": _rect(-10, 190, 0, 210), "C": _rect(40, 10, 50, 30), "D": _rect(40, 210, 50, 230)}

# three parallel routes sharing the same gap, with a box the moved run must not pierce
THREE_ROUTES = {
    0: [_p(10, 0), _p(60, 0), _p(60, 100), _p(110, 100)],
    1: [_p(10, 20), _p(60, 20), _p(60, 120), _p(110, 120)],
    2: [_p(10, 40), _p(60, 40), _p(60, 140), _p(110, 140)],
}
THREE_EDGES = {0: {"from": "A", "to": "D"}, 1: {"from": "B", "to": "E"}, 2: {"from": "C", "to": "F"}}
THREE_RECTS = {
    "A": _rect(0, -10, 10, 10), "B": _rect(0, 10, 10, 30), "C": _rect(0, 30, 10, 50),
    "D": _rect(110, 90, 120, 110), "E": _rect(110, 110, 120, 130), "F": _rect(110, 130, 120, 150),
}

CASES = [
    {"id": "parallel-moves-apart", "routes": PARALLEL_ROUTES, "edges": PARALLEL_EDGES, "rects": PARALLEL_RECTS},
    {"id": "self-and-outer-not-movable", "routes": PARALLEL_ROUTES, "edges": NOT_MOVABLE_EDGES, "rects": PARALLEL_RECTS},
    {"id": "far-apart-no-move", "routes": FAR_APART_ROUTES, "edges": PARALLEL_EDGES, "rects": FAR_APART_RECTS},
    {"id": "three-parallel", "routes": THREE_ROUTES, "edges": THREE_EDGES, "rects": THREE_RECTS},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_move_apart_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "moveApart", "routes": case["routes"], "edges": case["edges"], "rects": case["rects"]})
    py_result = move_apart(case["routes"], case["edges"], case["rects"])
    assert {str(k): v for k, v in py_result.items()} == node_result
