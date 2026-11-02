"""End-to-end tests for Diagram.tornado()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_tornado_renders():
    d = Diagram(width=500, height=350)
    d.tornado([{"label": "原材料費", "low": 850, "high": 1150}, {"label": "為替", "low": 940, "high": 1060}], x=0, y=0, width=500, base=1000, unit="百万円")
    svg = d.render_svg()
    _ok(svg)
    assert "原材料費" in svg
