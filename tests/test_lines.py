"""Golden-master tests for lines_band()/burndown_band()/burnup_band()/
strategy_canvas_band() against Node's lines()/burndown()/burnup()/strategyCanvas() (all
exported — live-tested via the shared dummy width function, same technique as
test_plane.py). Each ultimately produces a "plane" band, laid out with
plane.layout_plane() — see test_plane.py for why `paths` is compared with a tolerance."""

import pytest

from svg_diagram.lines import burndown_band, burnup_band, lines_band, strategy_canvas_band
from svg_diagram.plane import layout_plane, render_plane

from _approx import approx

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}
GEOMETRY_KEYS = ("x", "y", "w", "h", "labelSize", "bounds", "axisX", "axisY", "plotL", "plotR", "plotT", "plotB", "yDown", "ticks", "grid", "texts", "points", "lines", "paths", "dims", "labelBoxes", "obstacles", "clashes")


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {
        "kind": "lines",
        "req": {"series": [{"label": "売上", "values": [10, 20, 15, 30]}, {"label": "目標", "values": [10, 15, 20, 25], "ideal": True}], "opts": {"x": {"categories": ["1Q", "2Q", "3Q", "4Q"]}, "target": {"at": 25, "label": "目標"}}},
        "fn": lambda req: lines_band(req["series"], req["opts"]),
    },
    {
        "kind": "burndown",
        "req": {"spec": {"total": 100, "days": 10, "actual": [100, 90, 80, None, None, None, None, None, None, None, None]}, "opts": {}},
        "fn": lambda req: burndown_band(req["spec"], req["opts"]),
    },
    {
        "kind": "burnup",
        "req": {"spec": {"scope": 50, "days": 10, "done": [0, 5, 10, None, None, None, None, None, None, None, None]}, "opts": {}},
        "fn": lambda req: burnup_band(req["spec"], req["opts"]),
    },
    {
        "kind": "strategyCanvas",
        "req": {"factors": ["価格", "品質", "速度"], "series": [{"label": "自社", "values": [4, 3, 5]}, {"label": "競合", "values": [2, 5, 3]}], "opts": {}},
        "fn": lambda req: strategy_canvas_band(req["factors"], req["series"], req["opts"]),
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["kind"])
def test_layout_lines_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutLines", "linesKind": case["kind"], "x": 0, "y": 0, "w": 600, **case["req"]})
    band = case["fn"](case["req"])
    py_result = layout_plane(band, 0, 0, 600, _width_of, ROLES)
    for key in GEOMETRY_KEYS:
        assert approx(py_result.get(key), node_result.get(key)), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["kind"])
def test_render_lines_matches_node(node_golden, case):
    band = case["fn"](case["req"])
    laid = layout_plane(band, 0, 0, 600, _width_of, ROLES)
    node_result = node_golden.call({"kind": "renderPlane", "band": laid})
    py_result = render_plane(laid)
    assert py_result == node_result


def test_lines_rejects_too_many_series():
    series = [{"label": f"S{i}", "values": [1, 2, 3]} for i in range(7)]
    with pytest.raises(ValueError):
        lines_band(series, {"x": {"categories": ["a", "b", "c"]}})


def test_burndown_rejects_non_integer_days():
    with pytest.raises(ValueError):
        burndown_band({"total": 100, "days": 2.5, "actual": [100]})


def test_burnup_rejects_single_day_scope():
    with pytest.raises(ValueError):
        burnup_band({"scope": [10], "days": 5, "done": [0]})
