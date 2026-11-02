"""Golden-master tests for harvey_band()/layout_chart()/render_chart() against Node's
harvey()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy
width function, same technique as test_butterfly.py)."""

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.harvey import harvey_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {"rows": ["A社", "B社"], "cols": ["価格", "品質", "サポート"], "values": [[4, 2, None], [1, 4, 3]], "opts": {}, "w": 500},
    {"rows": [{"label": "X", "id": "rowx"}, "Y"], "cols": ["c1", "c2"], "values": [[0, 4], [2, 2]], "opts": {"corner": "評価", "highlight": ["c1"]}, "w": 400},
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_harvey_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "harvey", "rows": case["rows"], "cols": case["cols"], "values": case["values"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = harvey_band(case["rows"], case["cols"], case["values"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_harvey_matches_node(node_golden, case):
    band = harvey_band(case["rows"], case["cols"], case["values"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_harvey_rejects_out_of_range_value():
    with pytest.raises(ValueError):
        harvey_band(["A"], ["x"], [[5]])


def test_harvey_rejects_duplicate_rows():
    with pytest.raises(ValueError):
        harvey_band(["A", "A"], ["x"], [[1], [2]])
