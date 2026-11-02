"""End-to-end tests for Diagram.waterfall()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_waterfall_vertical_renders():
    d = Diagram(width=500, height=400)
    d.waterfall([{"label": "開始", "value": 100}, {"label": "増加A", "value": 30}, {"label": "減少B", "value": -50}, {"label": "合計", "kind": "total"}], x=0, y=0, width=500)
    svg = d.render_svg()
    _ok(svg)
    assert "開始" in svg


def test_waterfall_horizontal_renders():
    d = Diagram(width=600, height=400)
    d.waterfall(
        [
            {"label": "開始残高", "value": 1000},
            {"label": "売上", "value": 500},
            {"label": "費用", "value": -300},
            {"label": "小計", "kind": "subtotal"},
            {"label": "税金", "value": -100},
            {"label": "最終", "kind": "total"},
        ],
        x=0,
        y=0,
        width=600,
        direction="h",
        unit="万円",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "万円" in svg
