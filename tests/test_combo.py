"""Golden-master tests for combo_band()/layout_chart()/render_chart() against Node's
combo()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy width
function, same technique as test_bubble.py). Includes a case with two line series (exercises
the dashed-second-line / shape-index path) and series with ids (anchors)."""

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.combo import combo_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {
        "categories": ["1月", "2月", "3月", "4月"],
        "series": [{"label": "売上", "type": "bar", "values": [100, 120, 90, 140]}, {"label": "利益率", "type": "line", "values": [10, 12, 8, 15]}],
        "opts": {"y": {"unit": "億円"}, "y2": {"unit": "%"}},
        "w": 600,
    },
    {
        "categories": ["A", "B", "C"],
        "series": [{"label": "X", "type": "bar", "values": [10, 20, 15]}, {"label": "Y", "type": "bar", "values": [5, 10, 8]}],
        "opts": {"stack": True},
        "w": 500,
    },
    {
        "categories": ["A", "B", "C"],
        "series": [{"label": "棒", "type": "bar", "values": [10, 20, 15], "id": "barx"}, {"label": "線1", "type": "line", "values": [1, 2, 3], "id": "line1"}, {"label": "線2", "type": "line", "values": [3, 2, 1]}],
        "opts": {},
        "w": 600,
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_combo_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "combo", "categories": case["categories"], "series": case["series"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = combo_band(case["categories"], case["series"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_combo_matches_node(node_golden, case):
    band = combo_band(case["categories"], case["series"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_combo_rejects_bar_on_right_axis():
    with pytest.raises(ValueError):
        combo_band(["A", "B"], [{"label": "X", "type": "bar", "values": [1, 2], "axis": "right"}])


def test_combo_requires_left_axis_series():
    with pytest.raises(ValueError):
        combo_band(["A", "B"], [{"label": "X", "type": "line", "values": [1, 2], "axis": "right"}])
