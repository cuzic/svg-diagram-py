"""Golden-master tests for bubble_band()/layout_chart()/render_chart() against Node's
bubble()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy
width function, same technique as test_harvey.py). Includes a case where a point's bubble
radius forces the axis-widening loop to grow the scale past the raw data range."""

import pytest

from svg_diagram.bubble import bubble_band
from svg_diagram.charts import layout_chart, render_chart

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {
        "points": [{"label": "製品A", "x": 10, "y": 20, "size": 100}, {"label": "製品B", "x": 30, "y": 5, "size": 400}, {"label": "製品C", "x": 5, "y": 35, "size": 50}],
        "opts": {"x": {"title": "成長率"}, "y": {"title": "シェア"}, "sizeTitle": "売上", "sizeUnit": "億円"},
        "w": 600,
    },
    {"points": [{"label": "X", "x": 1, "y": 1, "size": 10, "id": "px"}, {"label": "Y", "x": 2, "y": 2, "size": 20}], "opts": {"x": {"line": 1.5, "lineLabel": "閾値"}}, "w": 500},
    {"points": [{"label": "小", "x": 0, "y": 0, "size": 5}, {"label": "大", "x": 10, "y": 10, "size": 2000}], "opts": {}, "w": 500},
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_bubble_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "bubble", "points": case["points"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = bubble_band(case["points"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_bubble_matches_node(node_golden, case):
    band = bubble_band(case["points"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_bubble_rejects_nonpositive_size():
    with pytest.raises(ValueError):
        bubble_band([{"label": "A", "x": 1, "y": 1, "size": 0}])


def test_bubble_rejects_duplicate_labels():
    with pytest.raises(ValueError):
        bubble_band([{"label": "A", "x": 1, "y": 1, "size": 1}, {"label": "A", "x": 2, "y": 2, "size": 1}])
