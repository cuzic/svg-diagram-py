"""Golden-master tests for stacked_bars_band()/mekko_band()/layout_chart()/render_chart()
against Node's stackedBars()/mekko()/layoutChart()/renderChart() (all exported —
live-tested via the shared dummy width function, same technique as test_waterfall.py)."""

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.stacked import mekko_band, stacked_bars_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {
        "fn": stacked_bars_band,
        "chart_kind": "stackedBars",
        "columns": [{"label": "2023", "parts": [{"label": "国内", "value": 60}, {"label": "海外", "value": 40}]}, {"label": "2024", "parts": [{"label": "国内", "value": 55}, {"label": "海外", "value": 65}]}],
        "opts": {"unit": "億円"},
        "w": 500,
    },
    {
        "fn": stacked_bars_band,
        "chart_kind": "stackedBars",
        "columns": [{"label": "A", "parts": [{"label": "x", "value": 3}, {"label": "y", "value": 7}]}, {"label": "B", "parts": [{"label": "x", "value": 5}, {"label": "y", "value": 5}]}],
        "opts": {"percent": True},
        "w": 400,
    },
    {
        "fn": mekko_band,
        "chart_kind": "mekko",
        "columns": [{"label": "A社", "parts": [{"label": "製品", "value": 70}, {"label": "保守", "value": 30}]}, {"label": "B社", "parts": [{"label": "製品", "value": 40}, {"label": "保守", "value": 20}]}],
        "opts": {"unit": "億円"},
        "w": 400,
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: f"{c['chart_kind']}-{c['opts']}")
def test_layout_stacked_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": case["chart_kind"], "columns": case["columns"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = case["fn"](case["columns"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: f"{c['chart_kind']}-{c['opts']}")
def test_render_stacked_matches_node(node_golden, case):
    band = case["fn"](case["columns"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_stacked_bars_rejects_empty_columns():
    with pytest.raises(ValueError):
        stacked_bars_band([])


def test_mekko_rejects_zero_total_column():
    with pytest.raises(ValueError):
        mekko_band([{"label": "A", "parts": [{"label": "x", "value": 0}]}])
