"""End-to-end tests for Diagram.bars()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_bars_horizontal_renders():
    d = Diagram(width=600, height=200)
    d.bars([{"label": "計画", "value": 10}, {"label": "実行", "value": 25}, {"label": "確認", "value": 15}], x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert "計画" in svg


def test_bars_vertical_stack_renders():
    d = Diagram(width=400, height=300)
    d.bars([{"label": "A", "value": 10, "series": "a"}, {"label": "B", "value": 25, "series": "b"}], x=0, y=0, width=400, direction="v", stack=True)
    svg = d.render_svg()
    _ok(svg)
    assert svg.count("<path") > 0


def test_bars_pareto_style_cumulative_renders():
    d = Diagram(width=500, height=320)
    d.bars([{"label": "傷", "value": 100}, {"label": "汚れ", "value": 60}, {"label": "欠け", "value": 40}], x=0, y=0, width=500, direction="v", cumulative={}, max_value=200)
    svg = d.render_svg()
    _ok(svg)
    assert "%" in svg
