"""Golden-master tests for text_lines() against Node's textLines()."""

import pytest

from svg_diagram.emit_common import text_lines

CASES = [
    {"lines": ["Start"], "x": 30, "top": 36, "size": 15, "fill": "#22201b"},
    {"lines": ["Start"], "x": 30, "top": 36, "size": 15, "weight": 700, "fill": "#22201b"},
    {"lines": ["行1", "行2", "行3"], "x": 30, "top": 36, "size": 14, "fill": "#22201b"},
    {"lines": ["centered"], "x": 100, "top": 36, "size": 15, "anchor": "middle", "fill": "#22201b"},
    {"lines": ["right"], "x": 100, "top": 36, "size": 15, "anchor": "end", "fill": "#22201b"},
    {"lines": ["mono text"], "x": 30, "top": 36, "size": 14, "mono": True, "fill": "#22201b"},
    {"lines": ["絵文字😀入り"], "x": 30, "top": 36, "size": 14, "fill": "#22201b"},
    {"lines": ["a & b < c>"], "x": 30, "top": 36, "size": 14, "fill": "#22201b"},
    {"lines": [], "x": 30, "top": 36, "size": 14, "fill": "#22201b"},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_text_lines_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "textLines", **case})
    py_result = text_lines(
        case["lines"],
        x=case["x"],
        top=case["top"],
        size=case["size"],
        weight=case.get("weight", 400),
        anchor=case.get("anchor", "start"),
        fill=case["fill"],
        mono=case.get("mono", False),
    )
    assert py_result == node_result
