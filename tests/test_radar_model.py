"""End-to-end tests for Diagram.radar()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_radar_renders():
    d = Diagram(width=500, height=450)
    d.radar(["速度", "耐久", "攻撃", "防御", "魔力"], [{"label": "A", "values": [3, 4, 2, 5, 1]}, {"label": "B", "values": [5, 2, 4, 1, 3]}], x=0, y=0, width=500)
    svg = d.render_svg()
    _ok(svg)
    assert "速度" in svg and "<path" in svg


def test_radar_single_series_fills_and_shows_values():
    d = Diagram(width=400, height=400)
    d.radar(["a", "b", "c"], [{"label": "solo", "values": [1, 2, 3]}], x=0, y=0, width=400, values=True, unit="pt")
    svg = d.render_svg()
    _ok(svg)
    assert "pt" in svg
