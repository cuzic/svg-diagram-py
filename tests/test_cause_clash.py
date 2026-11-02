"""Golden-master tests for and_clashes() against Node's andClashes()."""

from __future__ import annotations

import pytest

from svg_diagram.cause_clash import and_clashes

CASES = [
    {
        "id": "crosses",
        "edges": [
            {"from": "a", "to": "z", "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}]},
            {"from": "b", "to": "z", "points": [{"x": 50, "y": -50}, {"x": 50, "y": 50}]},
        ],
        "ands": [{"to": "z"}],
    },
    {
        "id": "runs-together",
        "edges": [
            {"from": "a", "to": "z", "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}]},
            {"from": "b", "to": "z", "points": [{"x": 10, "y": 2}, {"x": 110, "y": 2}]},
        ],
        "ands": [{"to": "z"}],
    },
    {
        "id": "no-clash-far-apart",
        "edges": [
            {"from": "a", "to": "z", "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}]},
            {"from": "b", "to": "z", "points": [{"x": 0, "y": 50}, {"x": 100, "y": 50}]},
        ],
        "ands": [{"to": "z"}],
    },
    {
        "id": "different-effects-not-compared",
        "edges": [
            {"from": "a", "to": "z1", "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}]},
            {"from": "b", "to": "z2", "points": [{"x": 50, "y": -50}, {"x": 50, "y": 50}]},
        ],
        "ands": [{"to": "z1"}, {"to": "z2"}],
    },
    {
        "id": "not-an-and-target-ignored",
        "edges": [
            {"from": "a", "to": "w", "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}]},
            {"from": "b", "to": "w", "points": [{"x": 50, "y": -50}, {"x": 50, "y": 50}]},
        ],
        "ands": [{"to": "z"}],
    },
    {
        "id": "three-way-and-with-one-clash",
        "edges": [
            {"from": "a", "to": "z", "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}]},
            {"from": "b", "to": "z", "points": [{"x": 50, "y": -50}, {"x": 50, "y": 50}]},
            {"from": "c", "to": "z", "points": [{"x": 0, "y": 200}, {"x": 100, "y": 200}]},
        ],
        "ands": [{"to": "z"}],
    },
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_and_clashes_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "andClashes", "edges": case["edges"], "ands": case["ands"]})
    py_result = and_clashes(case["edges"], case["ands"])
    assert py_result == node_result


def test_and_clashes_reports_each_pair_once():
    result = and_clashes(CASES[0]["edges"], CASES[0]["ands"])
    assert len(result) == 1
    assert result[0]["how"] == "crosses"


def test_runs_together_detected():
    result = and_clashes(CASES[1]["edges"], CASES[1]["ands"])
    assert len(result) == 1
    assert result[0]["how"] == "runs together with"
