"""Golden-master tests for flow_nodes.py, states_words.py, verify_base.py against Node's
lib/flow-nodes.ts, lib/states-words.ts, lib/verify-base.ts's statesProblems() (all exported
— live-tested via emit_cli.ts). Prerequisites for stateDiagram()/flowchart()."""

from __future__ import annotations

import pytest

from svg_diagram.flow_nodes import diamond_lines, diamond_points, onto_diamond, pill_lines, vertex_drops
from svg_diagram.states_words import states_words
from svg_diagram.verify_base import states_problems

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


DIAMOND_CASES = [
    {"id": "short-label", "label": "Yes?", "sub": None, "maxW": 200, "iconH": 0},
    {"id": "long-label-wraps", "label": "Is the order already paid in full", "sub": None, "maxW": 160, "iconH": 0},
    {"id": "with-sub-and-icon", "label": "In stock?", "sub": "warehouse check", "maxW": 180, "iconH": 24},
    {"id": "tiny-max-width", "label": "OK?", "sub": None, "maxW": 90, "iconH": 0},
    {"id": "floor-true", "label": "カタカナコトバがある", "sub": None, "maxW": 140, "iconH": 0, "floor": True},
]


@pytest.mark.parametrize("case", DIAMOND_CASES, ids=lambda c: c["id"])
def test_diamond_lines_matches_node(node_golden, case):
    floor = case.get("floor", False)
    req = {"kind": "diamondLines", "label": case["label"], "maxW": case["maxW"], "iconH": case["iconH"], "floor": floor}
    if case.get("sub") is not None:
        req["sub"] = case["sub"]
    node_result = node_golden.call(req)
    py_result = diamond_lines(case["label"], case.get("sub"), case["maxW"], case["iconH"], _width_of, ROLES, "phrase", floor)
    assert py_result == node_result


PILL_CASES = [
    {"id": "no-icon", "l": {"label": ["Start"], "sub": [], "w": 60, "h": 28}, "iconH": 0},
    {"id": "with-icon-and-sub", "l": {"label": ["End"], "sub": ["done"], "w": 50, "h": 48}, "iconH": 24},
]


@pytest.mark.parametrize("case", PILL_CASES, ids=lambda c: c["id"])
def test_pill_lines_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "pillLines", "l": case["l"], "iconH": case["iconH"]})
    assert pill_lines(case["l"], case["iconH"]) == node_result


RECT_CASES = [{"x": 10, "y": 20, "w": 80, "h": 40}, {"x": 0, "y": 0, "w": 100, "h": 50}]


@pytest.mark.parametrize("r", RECT_CASES, ids=lambda r: f"{r['w']}x{r['h']}")
def test_diamond_points_matches_node(node_golden, r):
    node_result = node_golden.call({"kind": "diamondPoints", "r": r})
    assert diamond_points(r) == node_result


ONTO_DIAMOND_CASES = [
    {"id": "vertical-from-top", "end": {"x": 50, "y": 20}, "next": {"x": 50, "y": 100}, "r": {"x": 10, "y": 20, "w": 80, "h": 40}},
    {"id": "vertical-from-bottom", "end": {"x": 30, "y": 60}, "next": {"x": 30, "y": 0}, "r": {"x": 10, "y": 20, "w": 80, "h": 40}},
    {"id": "horizontal-from-left", "end": {"x": 10, "y": 35}, "next": {"x": -50, "y": 35}, "r": {"x": 10, "y": 20, "w": 80, "h": 40}},
    {"id": "horizontal-from-right", "end": {"x": 90, "y": 50}, "next": {"x": 200, "y": 50}, "r": {"x": 10, "y": 20, "w": 80, "h": 40}},
    {"id": "diagonal-unchanged", "end": {"x": 10, "y": 20}, "next": {"x": 90, "y": 60}, "r": {"x": 10, "y": 20, "w": 80, "h": 40}},
]


@pytest.mark.parametrize("case", ONTO_DIAMOND_CASES, ids=lambda c: c["id"])
def test_onto_diamond_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "ontoDiamond", "end": case["end"], "next": case["next"], "r": case["r"]})
    assert onto_diamond(case["end"], case["next"], case["r"]) == node_result


DIAMOND_R = {"x": 100, "y": 0, "w": 80, "h": 60}
VERTEX_DROPS_CASES = [
    {
        "id": "three-straight-drops-all-move",
        "outs": [
            {"pts": [{"x": 100, "y": 60}, {"x": 100, "y": 150}], "target": {"x": 80, "y": 150, "w": 40, "h": 20}},
            {"pts": [{"x": 140, "y": 60}, {"x": 140, "y": 150}], "target": {"x": 120, "y": 150, "w": 40, "h": 20}},
            {"pts": [{"x": 180, "y": 60}, {"x": 180, "y": 150}], "target": {"x": 160, "y": 150, "w": 40, "h": 20}},
        ],
        "others": [{"x": 300, "y": 300, "w": 10, "h": 10}],
    },
    {
        "id": "one-not-straight-keeps-all",
        "outs": [
            {"pts": [{"x": 100, "y": 60}, {"x": 100, "y": 150}], "target": {"x": 80, "y": 150, "w": 40, "h": 20}},
            {"pts": [{"x": 140, "y": 60}, {"x": 160, "y": 100}, {"x": 160, "y": 150}], "target": {"x": 140, "y": 150, "w": 40, "h": 20}},
        ],
        "others": [],
    },
    {
        "id": "target-not-under-corner-keeps-all",
        "outs": [
            {"pts": [{"x": 140, "y": 60}, {"x": 140, "y": 150}], "target": {"x": 400, "y": 150, "w": 40, "h": 20}},
        ],
        "others": [],
    },
    {
        "id": "obstacle-blocks-move",
        "outs": [
            {"pts": [{"x": 140, "y": 60}, {"x": 140, "y": 150}], "target": {"x": 120, "y": 150, "w": 40, "h": 20}},
        ],
        "others": [{"x": 130, "y": 70, "w": 20, "h": 20}],
    },
]


@pytest.mark.parametrize("case", VERTEX_DROPS_CASES, ids=lambda c: c["id"])
def test_vertex_drops_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "vertexDrops", "outs": case["outs"], "r": DIAMOND_R, "others": case["others"]})
    py_result = vertex_drops(case["outs"], DIAMOND_R, case["others"])
    assert py_result == node_result


@pytest.mark.parametrize("flavor", [None, "flowchart"], ids=lambda f: f or "state")
def test_states_words_matches_node(node_golden, flavor):
    req: dict = {"kind": "statesWords"}
    if flavor is not None:
        req["flavor"] = flavor
    node_result = node_golden.call(req)
    assert states_words(flavor) == node_result


def _band_rect(x, y, w, h):
    return {"x": x, "y": y, "w": w, "h": h}


STATES_PROBLEMS_CASES = [
    {
        "id": "clean-no-problems",
        "band": {
            "x": 0, "y": 0, "w": 400, "h": 200,
            "anchors": [{"id": "a", **_band_rect(0, 0, 60, 30)}, {"id": "b", **_band_rect(300, 0, 60, 30)}],
            "edges": [{"from": "a", "to": "b", "points": [{"x": 60, "y": 15}, {"x": 300, "y": 15}]}],
            "labels": [],
        },
    },
    {
        "id": "route-through-unrelated-node",
        "band": {
            "x": 0, "y": 0, "w": 400, "h": 200,
            "anchors": [{"id": "a", **_band_rect(0, 0, 60, 30)}, {"id": "b", **_band_rect(300, 0, 60, 30)}, {"id": "c", **_band_rect(150, 0, 60, 30)}],
            "edges": [{"from": "a", "to": "b", "points": [{"x": 60, "y": 15}, {"x": 300, "y": 15}]}],
            "labels": [],
        },
    },
    {
        "id": "label-outside-figure",
        "band": {
            "x": 0, "y": 0, "w": 400, "h": 200,
            "anchors": [{"id": "a", **_band_rect(0, 0, 60, 30)}, {"id": "b", **_band_rect(300, 0, 60, 30)}],
            "edges": [{"from": "a", "to": "b", "points": [{"x": 60, "y": 15}, {"x": 300, "y": 15}]}],
            "labels": [{"text": "x", "edge": 0, **_band_rect(-30, 0, 20, 20)}],
        },
    },
    {
        "id": "label-overlaps-label",
        "band": {
            "x": 0, "y": 0, "w": 400, "h": 200,
            "anchors": [{"id": "a", **_band_rect(0, 0, 60, 30)}, {"id": "b", **_band_rect(300, 0, 60, 30)}],
            "edges": [
                {"from": "a", "to": "b", "points": [{"x": 60, "y": 15}, {"x": 300, "y": 15}]},
                {"from": "b", "to": "a", "points": [{"x": 300, "y": 60}, {"x": 60, "y": 60}]},
            ],
            "labels": [{"text": "x", "edge": 0, **_band_rect(100, 100, 30, 20)}, {"text": "y", "edge": 1, **_band_rect(110, 105, 30, 20)}],
        },
    },
    {
        "id": "flowchart-flavor-words",
        "band": {
            "x": 0, "y": 0, "w": 400, "h": 200, "flavor": "flowchart",
            "anchors": [{"id": "a", **_band_rect(0, 0, 60, 30)}, {"id": "b", **_band_rect(300, 0, 60, 30)}, {"id": "c", **_band_rect(150, 0, 60, 30)}],
            "edges": [{"from": "a", "to": "b", "points": [{"x": 60, "y": 15}, {"x": 300, "y": 15}]}],
            "labels": [],
        },
    },
]


@pytest.mark.parametrize("case", STATES_PROBLEMS_CASES, ids=lambda c: c["id"])
def test_states_problems_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "statesProblems", "band": case["band"]})
    assert states_problems(case["band"]) == node_result
