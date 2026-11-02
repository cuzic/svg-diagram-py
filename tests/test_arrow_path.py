"""Golden-master tests for arrow_path() against Node's arrowPath() (no `cuts` — that's
cause()'s hop-over routing, deferred to Phase H)."""

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
    )
    assert py_result == node_result


def test_arrow_path_raises_for_cuts():
    with pytest.raises(NotImplementedError):
        arrow_path([{"x": 0, "y": 0}, {"x": 10, "y": 0}], "#000", None, cuts=[{"x": 5, "y": 0}])
