"""End-to-end tests for Diagram.sankey()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_sankey_renders():
    d = Diagram(width=600, height=400)
    d.sankey(
        [{"id": "A", "label": "収入"}, {"id": "B", "label": "支出"}, {"id": "C", "label": "貯蓄"}],
        [{"from": "A", "to": "B", "value": 70}, {"from": "A", "to": "C", "value": 30}],
        x=0,
        y=0,
        width=600,
        unit="万円",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "収入" in svg and "<path" in svg
