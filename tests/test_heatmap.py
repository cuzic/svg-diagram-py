"""Golden-master tests for heatmap_band()/layout_chart()/render_chart() against Node's
heatmap()/layoutChart()/renderChart() (all exported — live-tested via the shared dummy
width function, same technique as test_bars.py)."""

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.heatmap import heatmap_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {"rows": ["1月", "2月"], "cols": ["0", "1", "2"], "values": [[100, 62, 48], [100, 58, None]], "opts": {"unit": "%", "corner": "登録月 ＼ 経過月"}, "w": 600},
    {"rows": ["A", "B", "C"], "cols": ["X", "Y"], "values": [[1, 2], [3, 4], [5, 6]], "opts": {"min": 0, "max": 6, "levels": 3}, "w": 500},
    {"rows": ["A", "B"], "cols": ["X", "Y"], "values": [[1, 2], [3, 4]], "opts": {"scale": False, "rowHeader": False}, "w": 400},
    {"rows": ["A", "B"], "cols": ["X", "Y"], "values": [[1.234, 2.5], [3.1, 4.9]], "opts": {"decimals": 1, "cellH": 60}, "w": 400},
]

@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_heatmap_matches_node(node_golden, case):
    # heatmap_band() takes a single `opts` dict with Node's own (camelCase) option names —
    # unlike bars_band()/word_art_band(), it is not exploded into Python keyword arguments.
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "heatmap", "rows": case["rows"], "cols": case["cols"], "values": case["values"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = heatmap_band(case["rows"], case["cols"], case["values"], case["opts"])
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_heatmap_matches_node(node_golden, case):
    band = heatmap_band(case["rows"], case["cols"], case["values"], case["opts"])
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_heatmap_rejects_empty_rows():
    with pytest.raises(ValueError):
        heatmap_band([], ["a"], [])


def test_heatmap_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        heatmap_band(["a"], ["x", "y"], [[1]])
