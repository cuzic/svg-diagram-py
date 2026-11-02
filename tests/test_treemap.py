"""Golden-master tests for treemap_band()/layout_chart()/render_chart() against Node's
treemap()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy width
function, same technique as test_radar.py)."""

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.treemap import treemap_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {"tree": [{"label": "北米", "value": 40}, {"label": "欧州", "value": 30}, {"label": "アジア", "value": 20}, {"label": "その他", "value": 10}], "opts": {}, "w": 500},
    {
        "tree": {"label": "全体", "children": [{"label": "A", "children": [{"label": "A1", "value": 10}, {"label": "A2", "value": 20}]}, {"label": "B", "value": 30, "tone": "danger"}]},
        "opts": {"unit": "億円", "percent": True},
        "w": 400,
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_treemap_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "treemap", "tree": case["tree"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = treemap_band(case["tree"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_treemap_matches_node(node_golden, case):
    band = treemap_band(case["tree"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_treemap_strict_raises_when_labels_dont_fit(node_golden):
    tree = {"label": "root", "children": [{"label": "X", "value": 1}, {"label": "Y", "value": 1}, {"label": "Z", "value": 1}]}
    with pytest.raises(RuntimeError):
        node_golden.call({"kind": "layoutChart", "chartKind": "treemap", "tree": tree, "x": 0, "y": 0, "w": 50, "opts": {"strict": True}})
    band = treemap_band(tree, {"strict": True})
    with pytest.raises(ValueError):
        layout_chart(band, 0, 0, 50, _width_of, ROLES, "phrase")


def test_treemap_rejects_all_zero_values():
    with pytest.raises(ValueError):
        treemap_band([{"label": "A", "value": 0}])
