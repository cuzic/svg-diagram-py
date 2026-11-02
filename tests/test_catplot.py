"""Golden-master tests for cat_band()/layout_cat() against Node's catplot()/boxplot()/
violinplot()/stripplot()/swarmplot()/pointplot()/barplot() (all exported — live-tested via
the shared dummy width function, same technique as test_combo.py)."""

from __future__ import annotations

import pytest

from svg_diagram.catplot import cat_band
from svg_diagram.charts import layout_chart

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


DATA = {"東京": [3, 7, 8, 5, 9, 2, 6, 7, 8, 5], "大阪": [4, 4, 5, 6, 3, 8, 7, 9, 2, 5], "名古屋": [1, 9, 3, 7, 5, 6, 8, 4, 5, 6]}

GROUPS_HUE = [
    {"label": "東京", "hues": [{"name": "午前", "values": [3, 7, 8, 5, 9]}, {"name": "午後", "values": [2, 6, 7, 8, 5]}]},
    {"label": "大阪", "hues": [{"name": "午前", "values": [4, 4, 5, 6, 3]}, {"name": "午後", "values": [8, 7, 9, 2, 5]}]},
]

CASES = [
    {"catFn": "boxplot", "data": DATA, "opts": {}},
    {"catFn": "violinplot", "data": DATA, "opts": {}},
    {"catFn": "stripplot", "data": DATA, "opts": {}},
    {"catFn": "swarmplot", "data": DATA, "opts": {}},
    {"catFn": "pointplot", "data": DATA, "opts": {}},
    {"catFn": "barplot", "data": DATA, "opts": {}},
    {"catFn": "boxplot", "data": DATA, "opts": {"dir": "h", "counts": True, "label": "売上"}},
    {"catFn": "catplot", "data": DATA, "opts": {"kind": ["violin", "strip"]}},
    {"catFn": "catplot", "data": GROUPS_HUE, "opts": {"kind": "box"}},
    {"catFn": "barplot", "data": DATA, "opts": {"error": "sd", "values": "mean"}},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['catFn']}-{c['opts']}")
def test_layout_cat_matches_node(node_golden, case):
    node_band = node_golden.call({"kind": "layoutChart", "chartKind": "catplot", "catFn": case["catFn"], "data": case["data"], "opts": case["opts"], "x": 0, "y": 0, "w": 640})
    band = cat_band(case["catFn"], case["data"], case["opts"], kind=None if case["catFn"] == "catplot" else {
        "boxplot": "box", "violinplot": "violin", "stripplot": "strip", "swarmplot": "swarm", "pointplot": "point", "barplot": "bar",
    }[case["catFn"]])
    py_result = layout_chart(band, 0, 0, 640, _width_of, ROLES)
    assert py_result == node_band


def test_catplot_rejects_strip_and_swarm_together():
    with pytest.raises(ValueError):
        cat_band("catplot", DATA, {"kind": ["strip", "swarm"]})


def test_catplot_rejects_mismatched_hues():
    with pytest.raises(ValueError):
        cat_band("catplot", [{"label": "a", "hues": [{"name": "x", "values": [1, 2]}]}, {"label": "b", "values": [1, 2]}])
