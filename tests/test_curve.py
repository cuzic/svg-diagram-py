"""Golden tests for curve geometry/rendering, against a fixture captured from the real
Node.js pipeline (layoutCurve()/renderCurve() aren't exported — same technique as
test_pyramid.py)."""

import json
from pathlib import Path

from svg_diagram.figures import curve_points, render_curve

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "golden" / "fixtures" / "curve_example.json").read_text(encoding="utf-8"))


def test_curve_points_matches_captured_node_layout():
    band = FIXTURE["laidOutBand"]
    result = curve_points(raw_points=FIXTURE["input"]["rawPoints"], axis_x=band["axisX"], axis_right=band["axisRight"], axis_top=band["axisTop"], axis_bottom=band["axisBottom"])
    for got, expected in zip(result, band["points"]):
        assert got["x"] == expected["x"]
        assert got["y"] == expected["y"]
        assert got["dropLine"] == expected["dropLine"]


def test_render_curve_matches_captured_node_output():
    band = FIXTURE["laidOutBand"]
    result = render_curve(
        axis_x=band["axisX"], axis_right=band["axisRight"], axis_top=band["axisTop"], axis_bottom=band["axisBottom"],
        points=band["points"], day="blue",
        y_top_label=FIXTURE["input"]["yTopLabel"], y_bottom_label=FIXTURE["input"]["yBottomLabel"], x_label=FIXTURE["input"]["xLabel"],
    )
    assert result == FIXTURE["renderedBody"]
