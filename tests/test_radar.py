"""Golden-master tests for radar_band()/layout_chart()/render_chart() against Node's
radar()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy width
function, same technique as test_sankey.py)."""

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.radar import radar_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {"axes": ["速度", "耐久", "攻撃", "防御", "魔力"], "series": [{"label": "A", "values": [3, 4, 2, 5, 1]}, {"label": "B", "values": [5, 2, 4, 1, 3]}], "opts": {}, "w": 500},
    {"axes": ["a", "b", "c"], "series": [{"label": "solo", "values": [1, 2, 3], "id": "s1"}], "opts": {"values": True, "unit": "pt"}, "w": 400},
    {"axes": ["a", "b", "c", "d"], "series": [{"label": "S1", "values": [1, 2, 3, 4]}], "opts": {"min": 0, "max": 10, "rings": 5, "fill": False}, "w": 400},
    {
        "axes": ["a", "b", "c"],
        "series": [
            {"label": "Series One Long Name", "values": [1, 2, 3]},
            {"label": "Series Two", "values": [2, 3, 1]},
            {"label": "Series Three", "values": [3, 1, 2]},
            {"label": "Series Four", "values": [1, 1, 1]},
        ],
        "opts": {},
        "w": 350,
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_radar_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "radar", "axes": case["axes"], "series": case["series"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = radar_band(case["axes"], case["series"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_radar_matches_node(node_golden, case):
    band = radar_band(case["axes"], case["series"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_radar_rejects_too_few_axes():
    with pytest.raises(ValueError):
        radar_band(["a", "b"], [{"label": "S", "values": [1, 2]}])


def test_radar_rejects_too_many_series():
    axes = ["a", "b", "c"]
    series = [{"label": f"S{i}", "values": [1, 1, 1]} for i in range(5)]
    with pytest.raises(ValueError):
        radar_band(axes, series)
