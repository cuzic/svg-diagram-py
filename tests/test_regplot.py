"""Golden-master tests for reg_band()/layout_reg() against Node's regplot()/residplot()
(all exported — live-tested via the shared dummy width function, same technique as
test_catplot.py)."""

from __future__ import annotations

import pytest

from svg_diagram.charts import layout_chart
from svg_diagram.regplot import reg_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


X = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
Y = [2.1, 3.9, 6.2, 7.8, 10.1, 12.3, 13.9, 16.2, 17.8, 20.1, 22.3, 23.9]
GROUP = ["a", "b"] * 6

CASES = [
    {"regFn": "regplot", "data": {"x": X, "y": Y}, "opts": {}},
    {"regFn": "regplot", "data": {"x": X, "y": Y}, "opts": {"order": 2, "stats": True}},
    {"regFn": "regplot", "data": {"x": X, "y": Y}, "opts": {"lowess": True}},
    {"regFn": "regplot", "data": {"x": X, "y": Y, "group": GROUP}, "opts": {"stats": True}},
    {"regFn": "residplot", "data": {"x": X, "y": Y}, "opts": {}},
    {"regFn": "residplot", "data": {"x": X, "y": Y}, "opts": {"lowess": True}},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['regFn']}-{c['opts']}")
def test_layout_reg_matches_node(node_golden, case):
    node_band = node_golden.call({"kind": "layoutChart", "chartKind": "regplot", "regFn": case["regFn"], "data": case["data"], "opts": case["opts"], "x": 0, "y": 0, "w": 640})
    band = reg_band(case["regFn"], case["regFn"] == "residplot", case["data"], case["opts"])
    py_result = layout_chart(band, 0, 0, 640, _width_of, ROLES)
    assert py_result == node_band


def test_regplot_rejects_lowess_with_order():
    with pytest.raises(ValueError):
        reg_band("regplot", False, {"x": X, "y": Y}, {"lowess": True, "order": 2})


def test_regplot_rejects_too_few_points_for_order():
    with pytest.raises(ValueError):
        reg_band("regplot", False, {"x": [1, 2, 3], "y": [1, 2, 3]}, {"order": 3})
