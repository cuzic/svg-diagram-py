"""Golden-master tests for multi_band()/layout_multi() against Node's hist2d()/jointplot()/
kde2d()/pairplot() (all exported — live-tested via the shared dummy width function, same
technique as test_catplot.py)."""

from __future__ import annotations

import pytest

from svg_diagram.charts import layout_chart
from svg_diagram.multiplot import multi_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


X = [12, 15, 14, 18, 22, 19, 17, 13, 16, 21, 20, 14, 15, 18, 25, 11, 16, 19, 23, 17]
Y = [5, 8, 7, 11, 14, 10, 9, 6, 9, 13, 12, 7, 8, 10, 16, 4, 9, 11, 15, 10]
GROUP = ["a", "b"] * 10
PAIR_DATA = {"身長": X, "体重": Y, "年齢": [30, 32, 28, 40, 45, 35, 33, 29, 31, 38, 36, 28, 30, 34, 44, 26, 31, 37, 42, 33]}

MULTI_MODE_FOR: dict[str, str] = {"hist2d": "hist2d", "jointplot": "joint", "kde2d": "kde2d", "pairplot": "pair"}

CASES = [
    {"multiFn": "hist2d", "data": {"x": X, "y": Y}, "opts": {}},
    {"multiFn": "kde2d", "data": {"x": X, "y": Y}, "opts": {}},
    {"multiFn": "jointplot", "data": {"x": X, "y": Y}, "opts": {"xLabel": "身長", "yLabel": "体重"}},
    {"multiFn": "jointplot", "data": {"x": X, "y": Y, "group": GROUP}, "opts": {}},
    {"multiFn": "pairplot", "data": PAIR_DATA, "opts": {}},
    {"multiFn": "pairplot", "data": PAIR_DATA, "opts": {"corner": True}},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['multiFn']}-{c['opts']}")
def test_layout_multi_matches_node(node_golden, case):
    node_band = node_golden.call({"kind": "layoutChart", "chartKind": "multiplot", "multiFn": case["multiFn"], "data": case["data"], "opts": case["opts"], "x": 0, "y": 0, "w": 640})
    band = multi_band(case["multiFn"], MULTI_MODE_FOR[case["multiFn"]], case["data"], case["opts"])
    py_result = layout_chart(band, 0, 0, 640, _width_of, ROLES)
    assert py_result == node_band


def test_multiplot_rejects_too_few_pair_vars():
    with pytest.raises(ValueError):
        multi_band("pairplot", "pair", {"身長": X}, {})


def test_multiplot_rejects_mismatched_xy_length():
    with pytest.raises(ValueError):
        multi_band("hist2d", "hist2d", {"x": X, "y": Y[:5]}, {})
