"""Golden-master tests for render_status() against Node's renderStatus()."""

import pytest

from svg_diagram.emit_boxes import render_status

CASES = [
    {"x": 10, "y": 10, "w": 80, "h": 24, "textY": 27, "text": "draft", "status": "draft"},
    {"x": 10, "y": 10, "w": 100, "h": 24, "textY": 27, "text": "検証中", "status": "wip"},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_render_status_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "renderStatus", **case})
    py_result = render_status(x=case["x"], y=case["y"], w=case["w"], h=case["h"], text_y=case["textY"], text=case["text"], status=case["status"])
    assert py_result == node_result
