"""End-to-end tests for Diagram.butterfly()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_butterfly_renders():
    d = Diagram(width=500, height=300)
    d.butterfly([{"label": "機能A", "left": 40, "right": 60}, {"label": "機能B", "left": 80, "right": 20}], x=0, y=0, width=500, left_label="自社", right_label="競合", unit="%")
    svg = d.render_svg()
    _ok(svg)
    assert "自社" in svg and "競合" in svg
