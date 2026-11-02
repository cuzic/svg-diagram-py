"""End-to-end tests for Diagram.bubble()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_bubble_renders():
    d = Diagram(width=600, height=500)
    d.bubble(
        [{"label": "製品A", "x": 10, "y": 20, "size": 100}, {"label": "製品B", "x": 30, "y": 5, "size": 400}, {"label": "製品C", "x": 5, "y": 35, "size": 50}],
        x=0,
        y=0,
        width=600,
        x_axis={"title": "成長率"},
        y_axis={"title": "シェア"},
        size_title="売上",
        size_unit="億円",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "製品A" in svg and "成長率" in svg
