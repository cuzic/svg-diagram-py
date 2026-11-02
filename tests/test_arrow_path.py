"""Golden-master tests for arrow_path() against Node's arrowPath(), including `cuts`
(cause()'s hop-over routing, ADR 0028)."""

import pytest

from svg_diagram.emit_common import arrow_path

CASES = [
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "color": "#22201b"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 100}], "color": "#b91c1c", "line": "dashed"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "color": "#1f6e73", "width": 3},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "color": "#b91c1c", "width": 2.5, "headAt": "both"},
    {"points": [{"x": 0, "y": 0}, {"x": 60, "y": 0}, {"x": 60, "y": 80}], "color": "#22201b"},
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "color": "#22201b", "line": "dashed", "end": "bar"},
    {"points": [{"x": 0, "y": 0}, {"x": 0, "y": 100}], "color": "#22201b"},
    # with cuts (hop-over bumps): one cut on the first segment of an elbow arrow
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}], "color": "#111111", "cuts": [{"x": 50, "y": 0, "side": {"x": 0, "y": 1}, "r": 6}]},
    # two cuts on the same segment, in written order (the path sorts them by position along the run)
    {
        "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}], "color": "#111111", "line": "dashed",
        "cuts": [{"x": 30, "y": 0, "side": {"x": 0, "y": 1}, "r": 5}, {"x": 70, "y": 0, "side": {"x": 0, "y": -1}, "r": 5}],
    },
    # a cut on the second (vertical) segment, bulging sideways
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}], "color": "#111111", "line": "dashed", "cuts": [{"x": 100, "y": 40, "side": {"x": 1, "y": 0}, "r": 6}]},
    # both ends get a head; the cut must not touch either arrowhead's run
    {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}], "color": "#111111", "headAt": "both", "cuts": [{"x": 50, "y": 0, "side": {"x": 0, "y": -1}, "r": 6}]},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_arrow_path_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "arrowPath", **case})
    py_result = arrow_path(
        case["points"],
        case["color"],
        case.get("line"),
        case.get("width", 2),
        case.get("headAt", "end"),
        case.get("end", "arrow"),
        case.get("cuts"),
    )
    assert py_result == node_result
