"""End-to-end test for Diagram.clustermap()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_clustermap_renders():
    d = Diagram(width=600, height=400)
    d.clustermap(["A店", "B店", "C店"], ["朝", "昼", "夜"], [[3, 9, 4], [8, 2, 9], [4, 8, 3]], x=0, y=0, width=500, opts={"unit": "件"})
    svg = d.render_svg()
    _ok(svg)
    assert "A店" in svg
