"""End-to-end tests for Diagram.harvey()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_harvey_renders():
    d = Diagram(width=500, height=300)
    d.harvey(["A社", "B社"], ["価格", "品質", "サポート"], [[4, 2, None], [1, 4, 3]], x=0, y=0, width=500)
    svg = d.render_svg()
    _ok(svg)
    assert "A社" in svg
