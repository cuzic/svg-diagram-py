"""Golden-master tests for sankey_band()/layout_chart()/render_chart() against Node's
sankey()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy width
function, same technique as test_heatmap.py)."""

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.sankey import sankey_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {
        "nodes": ["A", "B", "C", "D"],
        "links": [{"from": "A", "to": "B", "value": 10}, {"from": "A", "to": "C", "value": 5}, {"from": "B", "to": "D", "value": 10}, {"from": "C", "to": "D", "value": 5}],
        "opts": {},
        "w": 600,
    },
    {
        "nodes": [{"id": "A", "label": "収入"}, {"id": "B", "label": "支出", "tone": "danger"}, {"id": "C", "label": "貯蓄"}],
        "links": [{"from": "A", "to": "B", "value": 70, "tone": "danger"}, {"from": "A", "to": "C", "value": 30}],
        "opts": {"unit": "万円", "align": "left"},
        "w": 500,
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_sankey_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "sankey", "nodes": case["nodes"], "links": case["links"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = sankey_band(case["nodes"], case["links"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_sankey_matches_node(node_golden, case):
    band = sankey_band(case["nodes"], case["links"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_sankey_rejects_cycle():
    with pytest.raises(ValueError):
        sankey_band(["A", "B"], [{"from": "A", "to": "B", "value": 1}, {"from": "B", "to": "A", "value": 1}])


def test_sankey_rejects_unknown_node():
    with pytest.raises(ValueError):
        sankey_band(["A", "B"], [{"from": "A", "to": "C", "value": 1}])
