"""Golden-master tests for quadrant_band()/layout_quadrant()/render_quadrant() against
Node's quadrant()/layoutQuadrant()/renderQuadrant() (all exported — live-tested via the
shared dummy width function, same technique as test_combo.py)."""

from __future__ import annotations

import pytest

from svg_diagram.quadrant import layout_quadrant, quadrant_band, render_quadrant

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {"opts": {"preset": "bcg", "items": [{"label": "製品A", "cell": [0, 0], "size": 40}, {"label": "製品B", "at": [0.8, 0.9], "size": 120}]}, "w": 700},
    {"opts": {"preset": "nineBox", "items": [{"id": "a", "label": "田中", "at": [0.8, 0.8]}, {"label": "佐藤", "cell": [1, 1]}]}, "w": 700},
    {"opts": {"x": {"title": "価格", "low": "安い", "high": "高い"}, "y": {"title": "品質", "low": "低い", "high": "高い"}, "crosshair": True, "items": [{"id": "a", "label": "自社", "at": [0.5, 0.5]}, {"id": "b", "label": "競合", "at": [0.7, 0.3]}], "arrows": [{"from": "a", "to": "b", "label": "移動"}]}, "w": 700},
    {"opts": {"preset": "positioning", "items": [{"label": "A", "at": [0.2, 0.2]}, {"label": "B", "at": [0.8, 0.8]}], "regions": [{"title": "フロー", "points": [[0, 0], [1, 0], [1, 1], [0, 1]]}]}, "w": 700},
    {
        "opts": {
            "x": {"title": "x軸", "low": "低", "high": "高"}, "y": {"title": "y軸", "low": "低", "high": "高"},
            "items": [{"label": "A", "cell": [0, 0], "group": "グループ1", "size": 10}, {"label": "B", "cell": [0, 0], "group": "グループ2", "size": 30}, {"label": "C", "cell": [1, 1], "group": "グループ1", "size": 5}],
            "sizeTitle": "規模", "sizeUnit": "億円",
        },
        "w": 700,
    },
    {"opts": {"preset": "eisenhower", "allowEmpty": True}, "w": 600},
    {
        "opts": {
            "x": {"title": "x軸", "low": "低", "high": "高"}, "y": {"title": "y軸", "low": "低", "high": "高"}, "grid": [2, 2],
            "items": [{"label": f"項目{i}", "cell": [i % 2, (i // 2) % 2]} for i in range(10)],
        },
        "w": 600,
    },
    {
        "opts": {
            "x": {"title": "x軸", "low": "低", "high": "高"}, "y": {"title": "y軸", "low": "低", "high": "高"},
            "items": [{"label": f"項目{i}", "cell": [0, 0], "group": f"グループ{i}"} for i in range(6)],
        },
        "w": 700,
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"].get("preset", "custom")))
def test_layout_quadrant_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutQuadrant", "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]})
    band = quadrant_band(case["opts"])
    py_result = layout_quadrant(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    assert py_result == node_result


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"].get("preset", "custom")))
def test_render_quadrant_matches_node(node_golden, case):
    band = quadrant_band(case["opts"])
    laid = layout_quadrant(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderQuadrant", "band": laid})
    py_result = render_quadrant(laid)
    assert py_result == node_result


def test_quadrant_rejects_unknown_preset():
    with pytest.raises(ValueError):
        quadrant_band({"preset": "nope"})


def test_quadrant_rejects_axis_without_title():
    with pytest.raises(ValueError):
        quadrant_band({"x": {}, "y": {"title": "y"}})


def test_quadrant_rejects_both_cell_and_at():
    with pytest.raises(ValueError):
        quadrant_band({"x": {"title": "x"}, "y": {"title": "y"}, "items": [{"label": "a", "cell": [0, 0], "at": [0.1, 0.1]}]})
