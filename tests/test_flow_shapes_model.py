"""End-to-end tests for Diagram.chevron()/.funnel()/.cycle()/.venn()/.concentric()/.emblem()/.value_chain()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_chevron_renders():
    d = Diagram(width=600, height=100)
    d.chevron([{"label": "計画"}, {"label": "実行"}, {"label": "確認"}], x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert svg.count("<polygon") == 3


def test_funnel_renders():
    d = Diagram(width=600, height=300)
    d.funnel([{"label": "訪問", "value": 1000}, {"label": "登録", "value": 300}, {"label": "購入", "value": 50}], x=0, y=0, width=600, scale="value", show_rate=True)
    svg = d.render_svg()
    _ok(svg)
    assert "訪問" in svg and "%" in svg


def test_cycle_renders():
    d = Diagram(width=600, height=600)
    d.cycle([{"label": "A"}, {"label": "B"}, {"label": "C"}], x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert svg.count("<circle") == 3


def test_venn_renders():
    d = Diagram(width=600, height=400)
    d.venn([{"name": "A"}, {"name": "B"}], x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert svg.count("<circle") == 2


def test_concentric_renders():
    d = Diagram(width=600, height=400)
    d.concentric([{"label": "コア"}, {"label": "周辺"}], x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert "コア" in svg


def test_emblem_renders():
    d = Diagram(width=600, height=300)
    d.emblem([{"label": "課題", "sub": "3 件"}, {"label": "重要", "shape": "triangle", "tone": "danger"}], x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert "課題" in svg and "重要" in svg


def test_value_chain_renders():
    d = Diagram(width=600, height=300)
    d.value_chain(support=[{"label": "人事"}], primary=[{"label": "調達"}, {"label": "製造"}], x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert "人事" in svg and "マージン" in svg
