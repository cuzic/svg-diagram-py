"""End-to-end tests for Diagram.treemap()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_treemap_renders():
    d = Diagram(width=500, height=320)
    d.treemap([{"label": "北米", "value": 40}, {"label": "欧州", "value": 30}, {"label": "アジア", "value": 20}, {"label": "その他", "value": 10}], x=0, y=0, width=500)
    svg = d.render_svg()
    _ok(svg)
    assert "北米" in svg


def test_treemap_nested_with_percent():
    d = Diagram(width=400, height=300)
    d.treemap(
        {"label": "全体", "children": [{"label": "A", "children": [{"label": "A1", "value": 10}, {"label": "A2", "value": 20}]}, {"label": "B", "value": 30, "tone": "danger"}]},
        x=0,
        y=0,
        width=400,
        unit="億円",
        percent=True,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "%" in svg
