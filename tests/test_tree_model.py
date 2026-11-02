"""End-to-end tests for Diagram.tree()/.mindmap()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_tree_renders_org_chart():
    d = Diagram(width=900, height=300)
    d.tree({"label": "社長", "children": [{"label": "開発部", "id": "dev", "children": [{"label": "開発1課"}, {"label": "開発2課"}]}, {"label": "営業部"}]}, x=0, y=0, width=900)
    svg = d.render_svg()
    _ok(svg)
    assert svg.count("<rect") == 1 + 5
    assert "社長" in svg and "開発部" in svg


def test_mindmap_renders_radial():
    d = Diagram(width=900, height=400)
    d.mindmap({"label": "テーマ", "children": [{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}]}, x=0, y=0, width=900)
    svg = d.render_svg()
    _ok(svg)
    assert svg.count("<rect") == 1 + 5


def test_mindmap_fishbone_layout():
    d = Diagram(width=900, height=400)
    d.mindmap({"label": "問題", "children": [{"label": "人", "children": [{"label": "教育不足"}]}, {"label": "機械", "children": [{"label": "老朽化"}]}]}, x=0, y=0, width=900, layout="fishbone")
    svg = d.render_svg()
    _ok(svg)
    assert "問題" in svg and "教育不足" in svg
