"""End-to-end tests for Diagram.plane()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_plane_renders():
    d = Diagram(width=600, height=350)
    d.plane(
        {"x": {"label": "時間", "max": 100}, "y": {"label": "価値", "max": 60}, "points": [{"id": "a", "at": [20, 10], "label": "A"}, {"at": [50, 45], "label": "B点", "labelAt": "above"}], "lines": [{"from": "a", "to": [20, 0]}]},
        x=0,
        y=0,
        width=600,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "A" in svg and "B点" in svg


def test_plane_wardley_stages_renders():
    d = Diagram(width=500, height=350)
    d.plane({"x": {"max": 10}, "y": {"max": 10}, "stages": ["起源", "カスタム", "製品", "コモディティ"], "points": [{"at": [1, 5], "label": "自社", "evolves": {"to": 6}}]}, x=0, y=0, width=500)
    svg = d.render_svg()
    _ok(svg)
    assert "起源" in svg and "自社" in svg
