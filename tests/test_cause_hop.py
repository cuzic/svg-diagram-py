"""Golden-master tests for cause_crossings() against Node's causeCrossings()."""

from __future__ import annotations

import pytest

from svg_diagram.cause_hop import cause_crossings

_OVER = {"from": "x", "to": "y", "points": [{"x": 50, "y": 300}, {"x": 50, "y": 150}, {"x": 250, "y": 150}, {"x": 250, "y": 50}], "line": "solid", "reversed": True}
_UNDER_150 = {"from": "c", "to": "d", "points": [{"x": 150, "y": 0}, {"x": 150, "y": 300}], "line": "solid"}
_BAND = {"x": 0, "y": 0, "w": 400, "h": 300}

CASES = [
    {"id": "no-skip-real-crossing", "edges": [_OVER, _UNDER_150], "band": _BAND, "boxes": [], "ands": []},
    {"id": "dashed", "edges": [{**_OVER, "line": "dashed"}, _UNDER_150], "band": _BAND, "boxes": [], "ands": []},
    {
        "id": "corner",
        "edges": [_OVER, {"from": "c", "to": "d", "points": [{"x": 55, "y": 0}, {"x": 55, "y": 300}], "line": "solid"}],
        "band": _BAND, "boxes": [], "ands": [],
    },
    {
        "id": "arrowhead",
        "edges": [_OVER, {"from": "c", "to": "d", "points": [{"x": 150, "y": 0}, {"x": 150, "y": 160}], "line": "solid"}],
        "band": _BAND, "boxes": [], "ands": [],
    },
    {
        "id": "bar",
        "edges": [_OVER, {"from": "c", "to": "d", "points": [{"x": 150, "y": 0}, {"x": 150, "y": 163}], "line": "solid", "kind": "blocks"}],
        "band": _BAND, "boxes": [], "ands": [],
    },
    {
        "id": "neighbour",
        "edges": [_OVER, _UNDER_150, {"from": "e", "to": "f", "points": [{"x": 155, "y": 0}, {"x": 155, "y": 300}], "line": "solid"}],
        "band": _BAND, "boxes": [], "ands": [],
    },
    {
        "id": "and-arc",
        "edges": [_OVER, _UNDER_150], "band": _BAND, "boxes": [],
        "ands": [{"p0": {"x": 100, "y": 140}, "c": {"x": 150, "y": 160}, "p1": {"x": 200, "y": 140}}],
    },
    {"id": "band", "edges": [_OVER, _UNDER_150], "band": {"x": 0, "y": 0, "w": 400, "h": 155}, "boxes": [], "ands": []},
    {
        "id": "parallel",
        "edges": [_OVER, _UNDER_150, {"from": "g", "to": "h", "points": [{"x": 100, "y": 155}, {"x": 200, "y": 155}], "line": "solid"}],
        "band": _BAND, "boxes": [], "ands": [],
    },
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_cause_crossings_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "causeCrossings", "flow": "up", "band": case["band"], "boxes": case["boxes"], "ands": case["ands"], "edges": case["edges"]})
    py_result = cause_crossings(case["edges"], "up", case["band"], case["boxes"], case["ands"])
    assert py_result == node_result


def test_real_crossing_has_no_skip_reason():
    result = cause_crossings([_OVER, _UNDER_150], "up", _BAND, [], [])
    assert len(result) == 1
    assert "skipped" not in result[0]


def test_neighbour_flags_both_close_crossings():
    extra = {"from": "e", "to": "f", "points": [{"x": 155, "y": 0}, {"x": 155, "y": 300}], "line": "solid"}
    result = cause_crossings([_OVER, _UNDER_150, extra], "up", _BAND, [], [])
    assert len(result) == 2
    assert all(c["skipped"] == "neighbour" for c in result)
