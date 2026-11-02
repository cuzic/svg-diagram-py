"""Golden-master tests for waterfall_band()/layout_chart()/render_chart() against Node's
waterfall()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy
width function, same technique as test_treemap.py)."""

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.waterfall import waterfall_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {"steps": [{"label": "開始", "value": 100}, {"label": "増加A", "value": 30}, {"label": "減少B", "value": -50}, {"label": "合計", "kind": "total"}], "opts": {}, "w": 500},
    {
        "steps": [
            {"label": "開始残高", "value": 1000},
            {"label": "売上", "value": 500},
            {"label": "費用", "value": -300},
            {"label": "小計", "kind": "subtotal"},
            {"label": "税金", "value": -100},
            {"label": "最終", "kind": "total"},
        ],
        "opts": {"dir": "h", "unit": "万円"},
        "w": 600,
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_waterfall_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "waterfall", "steps": case["steps"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = waterfall_band(case["steps"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_waterfall_matches_node(node_golden, case):
    band = waterfall_band(case["steps"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_waterfall_rejects_too_few_steps():
    with pytest.raises(ValueError):
        waterfall_band([{"label": "A", "value": 1}])


def test_waterfall_rejects_mismatched_total():
    with pytest.raises(ValueError):
        waterfall_band([{"label": "A", "value": 10}, {"label": "B", "value": 999, "kind": "total"}])
