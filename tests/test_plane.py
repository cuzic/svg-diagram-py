"""Golden-master tests for plane_band()/layout_plane()/render_plane() against Node's
plane()/layoutPlane()/renderPlane() (all exported — live-tested via the shared dummy width
function, same technique as test_combo.py).

plane() is a standalone band type ("plane"), not part of the "chart" family — it has its
own layout_plane()/render_plane() pair, not charts.layout_chart()/render_chart().

Layout comparisons use a tolerant comparator (see _approx.py) because a path's arrow-tip
direction (and centripetal curve fitting for a non-monotone smooth path) can differ from
Node's by a floating-point ULP (Math.hypot vs math.hypot) — see plane.py's module
docstring. render_plane()'s output, compared with plain equality, is always exact."""

import pytest

from svg_diagram.plane import layout_plane, plane_band, render_plane

from _approx import approx

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {
        "opts": {"x": {"label": "時間", "max": 100}, "y": {"label": "価値", "max": 60}, "points": [{"id": "a", "at": [20, 10], "label": "A"}, {"at": [50, 45], "label": "B点", "labelAt": "above"}], "lines": [{"from": "a", "to": [20, 0]}]},
        "w": 600,
    },
    {"opts": {"x": {"max": 10}, "y": {"max": 10}, "stages": ["起源", "カスタム", "製品", "コモディティ"], "points": [{"at": [1, 5], "label": "自社", "evolves": {"to": 6}}]}, "w": 500},
    {"opts": {"x": {"max": 100}, "y": {"max": 60}, "paths": [{"through": [[0, 10], [20, 40], [50, 20], [80, 55]], "smooth": True, "arrow": True}]}, "w": 600},
    {"opts": {"x": {"max": 100}, "y": {"max": 60}, "points": [{"id": "a", "at": [10, 10]}, {"id": "b", "at": [70, 45]}], "dims": [{"from": "a", "to": "b", "label": "40 m", "side": "below"}]}, "w": 500},
    # non-monotone x: uses centripetal Catmull-Rom (hypot(...) ** 0.5), see module docstring
    {"opts": {"x": {"max": 100}, "y": {"max": 60}, "paths": [{"through": [[50, 10], [0, 40], [80, 20], [20, 55]], "smooth": True}]}, "w": 600},
]

GEOMETRY_KEYS = ("x", "y", "w", "h", "labelSize", "bounds", "axisX", "axisY", "plotL", "plotR", "plotT", "plotB", "yDown", "ticks", "grid", "texts", "points", "lines", "paths", "dims", "labelBoxes", "obstacles", "clashes")


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_plane_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutPlane", "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]})
    band = plane_band(case["opts"])
    py_result = layout_plane(band, 0, 0, case["w"], _width_of, ROLES)
    for key in GEOMETRY_KEYS:
        assert approx(py_result.get(key), node_result.get(key)), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_plane_matches_node(node_golden, case):
    band = plane_band(case["opts"])
    laid = layout_plane(band, 0, 0, case["w"], _width_of, ROLES)
    node_result = node_golden.call({"kind": "renderPlane", "band": laid})
    py_result = render_plane(laid)
    assert py_result == node_result


def test_plane_rejects_axis_without_max():
    with pytest.raises(ValueError):
        plane_band({"x": {}, "y": {"max": 10}})


def test_plane_rejects_evolves_outside_axis():
    with pytest.raises(ValueError):
        plane_band({"x": {"max": 10}, "y": {"max": 10}, "points": [{"at": [5, 5], "evolves": {"to": 20}}]})
