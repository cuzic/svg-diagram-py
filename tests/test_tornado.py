"""Golden-master tests for tornado_band()/layout_chart()/render_chart() against Node's
tornado()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy
width function, same technique as test_waterfall.py)."""

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.tornado import tornado_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {"items": [{"label": "原材料費", "low": 850, "high": 1150}, {"label": "為替", "low": 940, "high": 1060}, {"label": "人件費", "low": 980, "high": 1020}], "opts": {"base": 1000, "unit": "百万円"}, "w": 500},
    {"items": [{"label": "A", "low": 100, "high": 80}, {"label": "B", "low": 70, "high": 130}], "opts": {"base": 100, "sort": False, "lowTone": "danger", "highTone": "muted"}, "w": 400},
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_tornado_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "tornado", "items": case["items"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = tornado_band(case["items"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_tornado_matches_node(node_golden, case):
    band = tornado_band(case["items"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_tornado_requires_base():
    with pytest.raises(ValueError):
        tornado_band([{"label": "A", "low": 1, "high": 2}])


def test_tornado_rejects_empty_items():
    with pytest.raises(ValueError):
        tornado_band([], {"base": 10})
