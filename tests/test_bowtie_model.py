"""End-to-end tests for Diagram.bowtie()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_bowtie_renders():
    d = Diagram(width=1200, height=500)
    d.bowtie(
        {
            "hazard": "顧客データ", "top": "個人情報の漏えい",
            "threats": [{"label": "不正アクセス", "barriers": ["多要素認証", "アクセス制限"]}, {"label": "誤送信", "barriers": ["送信前の確認"]}],
            "consequences": [{"label": "信用の低下", "barriers": ["広報対応"]}, {"label": "賠償", "barriers": ["保険"]}],
        },
        x=0, y=0, width=1200,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "個人情報の漏えい" in svg and "不正アクセス" in svg and "賠償" in svg


def test_bowtie_max_node_w_auto_renders():
    d = Diagram(width=600, height=400)
    d.bowtie(
        {"top": "設備停止" * 3, "threats": [{"label": "A"}], "consequences": [{"label": "B"}]},
        x=0, y=0, width=600, max_node_w="auto",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "設備停止" in svg
