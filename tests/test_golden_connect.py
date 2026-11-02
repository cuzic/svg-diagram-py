"""Golden-master tests for render_connect() against Node's renderConnect() (straight-line case only)."""

import pytest

from svg_diagram.emit_boxes import render_connect

CASES = [
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "arrow": "end"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "arrow": "start"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "arrow": "both"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "arrow": "none"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 50}], "arrow": "end", "line": "dashed"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 50}], "arrow": "end", "line": "dotted"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 50}], "arrow": "end", "tone": "accent"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 50}], "arrow": "end", "tone": "danger"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 50}], "arrow": "end", "dim": True},
    {"points": [{"x": 10, "y": 10}, {"x": 60, "y": 10}, {"x": 60, "y": 90}], "arrow": "end"},  # multi-point polyline
    # Math.round half-to-even vs JS half-up: force a .5 boundary
    {"points": [{"x": 0.5, "y": 0.5}, {"x": 99.5, "y": 49.5}], "arrow": "end"},
    {"points": [{"x": -0.5, "y": -0.5}, {"x": 10, "y": 10}], "arrow": "end"},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_render_connect_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "connect", **case})
    py_result = render_connect(
        points=case["points"],
        arrow=case.get("arrow", "end"),
        line=case.get("line"),
        tone=case.get("tone"),
        dim=case.get("dim", False),
    )
    assert py_result == node_result


@pytest.mark.parametrize("bad_kwargs", [{"weight": "strong"}, {"line": "double"}, {"label": "x"}])
def test_render_connect_raises_for_out_of_scope_features(bad_kwargs):
    with pytest.raises(NotImplementedError):
        render_connect(points=[{"x": 0, "y": 0}, {"x": 1, "y": 1}], **bad_kwargs)
