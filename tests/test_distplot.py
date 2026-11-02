"""Golden-master tests for dist_band()/layout_dist() against Node's displot()/histplot()/
kdeplot()/ecdfplot()/rugplot() (all exported — live-tested via the shared dummy width
function, same technique as test_catplot.py)."""

from __future__ import annotations

import pytest

from svg_diagram.charts import layout_chart
from svg_diagram.distplot import dist_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


VALUES = [12, 15, 14, 18, 22, 19, 17, 13, 16, 21, 20, 14, 15, 18, 25, 11, 16, 19, 23, 17]
GROUPS = {"男性": [12, 15, 14, 18, 22, 19, 17, 13, 16, 21], "女性": [20, 14, 15, 18, 25, 11, 16, 19, 23, 17]}

DIST_KIND_FOR: dict[str, str] = {"histplot": "hist", "kdeplot": "kde", "ecdfplot": "ecdf", "rugplot": "rug"}

CASES = [
    {"distFn": "histplot", "data": VALUES, "opts": {}},
    {"distFn": "kdeplot", "data": VALUES, "opts": {}},
    {"distFn": "ecdfplot", "data": VALUES, "opts": {}},
    {"distFn": "rugplot", "data": VALUES, "opts": {}},
    {"distFn": "histplot", "data": GROUPS, "opts": {"bins": 6, "stat": "percent"}},
    {"distFn": "kdeplot", "data": GROUPS, "opts": {"bw": 0.6}},
    {"distFn": "displot", "data": VALUES, "opts": {"kind": ["hist", "kde", "rug"]}},
    {"distFn": "displot", "data": GROUPS, "opts": {"kind": ["hist", "rug"], "element": "step"}},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['distFn']}-{c['opts']}")
def test_layout_dist_matches_node(node_golden, case):
    node_band = node_golden.call({"kind": "layoutChart", "chartKind": "distplot", "distFn": case["distFn"], "data": case["data"], "opts": case["opts"], "x": 0, "y": 0, "w": 640})
    kind = DIST_KIND_FOR.get(case["distFn"], "hist")
    band = dist_band(case["distFn"], case["data"], case["opts"], kind)
    py_result = layout_chart(band, 0, 0, 640, _width_of, ROLES)
    assert py_result == node_band


def test_distplot_rejects_ecdf_with_hist():
    with pytest.raises(ValueError):
        dist_band("displot", VALUES, {"kind": ["hist", "ecdf"]}, "hist")


def test_distplot_rejects_empty_values():
    with pytest.raises(ValueError):
        dist_band("histplot", [], {}, "hist")
