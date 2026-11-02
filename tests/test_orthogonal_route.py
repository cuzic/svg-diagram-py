"""Golden-master tests for orthogonal_route.py's route_clear() against Node's routeClear()
(lib/orthogonal-route.ts, exported — live-tested via emit_cli.ts). Pure grid-search geometry,
the last-resort router bpmn() uses when a fixed list of shapes can't connect two boxes."""

from __future__ import annotations

import pytest

from svg_diagram.orthogonal_route import route_clear

BOUNDS = {"x": -40, "y": -200, "w": 500, "h": 400}

FROM = {"x": 0, "y": 0, "w": 40, "h": 20}
TO_RIGHT = {"x": 200, "y": 0, "w": 40, "h": 20}
TO_BELOW = {"x": 0, "y": 150, "w": 40, "h": 20}
TO_OFFSET = {"x": 200, "y": 150, "w": 40, "h": 20}
OBSTACLE = {"x": 100, "y": -10, "w": 40, "h": 40}

ROUTE_CASES = [
    {"id": "clear-horizontal", "opts": {"from": FROM, "to": TO_RIGHT, "boxes": [FROM, TO_RIGHT], "bounds": BOUNDS}},
    {"id": "clear-vertical", "opts": {"from": FROM, "to": TO_BELOW, "boxes": [FROM, TO_BELOW], "bounds": BOUNDS}},
    {"id": "offset-detour", "opts": {"from": FROM, "to": TO_OFFSET, "boxes": [FROM, TO_OFFSET], "bounds": BOUNDS}},
    {"id": "obstacle-forces-detour", "opts": {"from": FROM, "to": TO_RIGHT, "boxes": [FROM, TO_RIGHT, OBSTACLE], "bounds": BOUNDS}},
    {"id": "custom-margin-stub", "opts": {"from": FROM, "to": TO_RIGHT, "boxes": [FROM, TO_RIGHT, OBSTACLE], "bounds": BOUNDS, "margin": 12, "stub": 24}},
    {"id": "xs-ys-hints", "opts": {"from": FROM, "to": TO_OFFSET, "boxes": [FROM, TO_OFFSET], "bounds": BOUNDS, "xs": [120], "ys": [75]}},
    {
        "id": "others-ride-and-cross",
        "opts": {
            "from": FROM, "to": TO_RIGHT, "boxes": [FROM, TO_RIGHT], "bounds": BOUNDS,
            "others": [
                [{"x": 20, "y": 10}, {"x": 20, "y": 80}, {"x": 160, "y": 80}, {"x": 160, "y": 10}],
                [{"x": 100, "y": -50}, {"x": 100, "y": 50}],
            ],
        },
    },
    {"id": "unreachable-to-outside-bounds", "opts": {"from": FROM, "to": {"x": 5000, "y": 5000, "w": 40, "h": 20}, "boxes": [FROM, {"x": 5000, "y": 5000, "w": 40, "h": 20}], "bounds": BOUNDS}},
    {
        "id": "three-boxes-need-many-bends",
        "opts": {
            "from": {"x": 0, "y": 0, "w": 40, "h": 20},
            "to": {"x": 240, "y": 120, "w": 40, "h": 20},
            "boxes": [
                {"x": 0, "y": 0, "w": 40, "h": 20}, {"x": 240, "y": 120, "w": 40, "h": 20},
                {"x": 80, "y": -20, "w": 40, "h": 160}, {"x": 160, "y": -20, "w": 40, "h": 100},
            ],
            "bounds": BOUNDS,
        },
    },
]


@pytest.mark.parametrize("case", ROUTE_CASES, ids=lambda c: c["id"])
def test_route_clear_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "routeClear", "opts": case["opts"]})
    py_result = route_clear(case["opts"])
    assert py_result == node_result


def test_route_clear_returns_none_when_blocked():
    opts = {"from": FROM, "to": {"x": 5000, "y": 5000, "w": 40, "h": 20}, "boxes": [FROM, {"x": 5000, "y": 5000, "w": 40, "h": 20}], "bounds": BOUNDS}
    assert route_clear(opts) is None
