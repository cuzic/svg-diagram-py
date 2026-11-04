"""Golden-master tests for cluster_band()/layout_cluster() against Node's clustermap()
(exported — live-tested via the shared dummy width function, same technique as
test_catplot.py)."""

from __future__ import annotations

import pytest

from svg_diagram.charts import layout_chart
from svg_diagram.clustermap import cluster_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


ROWS = ["A店", "B店", "C店", "D店"]
COLS = ["朝", "昼", "夜"]
VALUES: list[list[float]] = [[3, 9, 4], [8, 2, 9], [4, 8, 3], [7, 3, 8]]

CASES = [
    {"opts": {}},
    {"opts": {"scale": "row"}},
    {"opts": {"scale": "col", "unit": "件"}},
    {"opts": {"rows": False}},
    {"opts": {"cols": False}},
    {"opts": {"rows": False, "cols": False, "values": False}},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c["opts"]))
def test_layout_cluster_matches_node(node_golden, case):
    node_band = node_golden.call({"kind": "layoutChart", "chartKind": "clustermap", "rows": ROWS, "cols": COLS, "values": VALUES, "opts": case["opts"], "x": 0, "y": 0, "w": 500})
    band = cluster_band(ROWS, COLS, VALUES, case["opts"])
    py_result = layout_chart(band, 0, 0, 500, _width_of, ROLES)
    assert py_result == node_band


def test_clustermap_rejects_too_few_rows():
    with pytest.raises(ValueError):
        cluster_band(["A"], COLS, [[1, 2, 3]], {})


def test_clustermap_rejects_mismatched_values_shape():
    with pytest.raises(ValueError):
        cluster_band(ROWS, COLS, [[1, 2], [1, 2], [1, 2], [1, 2]], {})
