"""Golden-master tests for route_search.py's head_crossings()/search_route() against Node's
headCrossings()/searchRoute() (lib/route-search.ts, both exported — live-tested via
emit_cli.ts). Pure A* grid search, the last-resort router for one long arrow of a layered
layout (layered-route.ts, not yet ported)."""

from __future__ import annotations

import pytest

from svg_diagram.route_search import head_crossings, search_route


def _p(x: float, y: float) -> dict:
    return {"x": x, "y": y}


def _box(x: float, y: float, w: float, h: float) -> dict:
    return {"x": x, "y": y, "w": w, "h": h}


BOUNDS = {"x": 0, "y": -100, "w": 500, "h": 300}

ROUTE_CASES = [
    {"id": "clear-straight", "start": _p(10, 50), "end": _p(300, 50), "boxes": [], "others": []},
    {"id": "one-obstacle-detour", "start": _p(10, 50), "end": _p(300, 50), "boxes": [_box(100, 20, 80, 60)], "others": []},
    {
        "id": "others-add-cross-and-along-cost",
        "start": _p(10, 50), "end": _p(300, 50), "boxes": [],
        "others": [[_p(50, -50), _p(50, 150)], [_p(0, 90), _p(300, 90)]],
    },
    {
        "id": "two-boxes-narrow-channel",
        "start": _p(10, 50), "end": _p(400, 50),
        "boxes": [_box(100, -80, 60, 120), _box(100, 60, 60, 120)],
        "others": [],
    },
    {
        "id": "head-reach-cost-near-tip",
        "start": _p(10, 10), "end": _p(300, 10), "boxes": [],
        "others": [[_p(150, -50), _p(150, 10)]],
    },
    {"id": "unreachable-returns-none", "start": _p(10, 50), "end": _p(300, 50), "boxes": [_box(0, -90, 500, 280)], "others": []},
    {"id": "custom-margin-and-stub", "start": _p(10, 50), "end": _p(300, 50), "boxes": [_box(100, 20, 80, 60)], "others": [], "opts": {"margin": 16, "stub": 30, "tail": 10}},
    {"id": "budget-tiny-may-fail-or-partial", "start": _p(10, 50), "end": _p(300, 50), "boxes": [_box(100, 20, 80, 60)], "others": [], "opts": {"budget": 5}},
]


@pytest.mark.parametrize("case", ROUTE_CASES, ids=lambda c: c["id"])
def test_search_route_matches_node(node_golden, case):
    opts = case.get("opts", {})
    node_result = node_golden.call({"kind": "searchRoute", "start": case["start"], "end": case["end"], "boxes": case["boxes"], "others": case["others"], "bounds": BOUNDS, "opts": opts})
    py_result = search_route(case["start"], case["end"], case["boxes"], case["others"], BOUNDS, **opts)
    assert py_result == node_result


HEAD_CROSSINGS_CASES = [
    {"id": "no-crossing", "paths": [[_p(0, 0), _p(100, 0)], [_p(0, 50), _p(100, 50)]]},
    {"id": "one-head-crossing", "paths": [[_p(0, 0), _p(50, 0), _p(50, 100)], [_p(60, 0), _p(60, 90), _p(100, 90)]]},
    {"id": "crossing-far-from-tip-does-not-count", "paths": [[_p(0, 0), _p(200, 0), _p(200, 100)], [_p(60, -50), _p(60, 50)]]},
]


@pytest.mark.parametrize("case", HEAD_CROSSINGS_CASES, ids=lambda c: c["id"])
def test_head_crossings_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "headCrossings", "paths": case["paths"]})
    assert head_crossings(case["paths"]) == node_result
