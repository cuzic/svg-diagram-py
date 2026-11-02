"""Golden-master tests for butterfly_band()/layout_chart()/render_chart() against Node's
butterfly()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy
width function, same technique as test_tornado.py)."""

import pytest

from svg_diagram.butterfly import butterfly_band
from svg_diagram.charts import layout_chart, render_chart

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {"rows": [{"label": "機能A", "left": 40, "right": 60}, {"label": "機能B", "left": 80, "right": 20}], "opts": {"leftLabel": "自社", "rightLabel": "競合", "unit": "%"}, "w": 500},
    {"rows": [{"label": "X", "left": 10, "right": 90}, {"label": "Y", "left": 50, "right": 50}], "opts": {"leftLabel": "前", "rightLabel": "後", "sort": "right", "leftTone": "muted", "rightTone": "danger"}, "w": 400},
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_butterfly_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "butterfly", "rows": case["rows"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = butterfly_band(case["rows"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_butterfly_matches_node(node_golden, case):
    band = butterfly_band(case["rows"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_butterfly_requires_labels():
    with pytest.raises(ValueError):
        butterfly_band([{"label": "A", "left": 1, "right": 2}], {})


def test_butterfly_rejects_all_zero():
    with pytest.raises(ValueError):
        butterfly_band([{"label": "A", "left": 0, "right": 0}], {"leftLabel": "L", "rightLabel": "R"})
