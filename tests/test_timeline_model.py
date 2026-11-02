"""End-to-end test for Diagram.timeline()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def test_timeline_renders():
    d = Diagram(width=900, height=150)
    d.timeline(x=0, y=0, width=900, now={"at": "2026-01-01"}, deadline={"label": "リリース", "at": "2026-06-30"}, marks=[{"label": "中間レビュー", "at": "2026-03-15"}], from_="2026-01-01", to="2026-12-31")
    svg = d.render_svg()
    minidom.parseString(svg)
    assert "リリース" in svg and "中間レビュー" in svg
    assert svg.count("<circle") == 3
