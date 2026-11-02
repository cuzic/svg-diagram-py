"""End-to-end test for Diagram.sequence()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def test_sequence_renders():
    d = Diagram(width=600, height=200)
    d.sequence(
        [{"id": "u", "label": "ユーザー"}, {"id": "s", "label": "サーバー"}],
        [{"from": "u", "to": "s", "label": "リクエスト"}, {"from": "s", "to": "u", "label": "レスポンス"}],
        x=0, y=0, width=600,
    )
    svg = d.render_svg()
    minidom.parseString(svg)
    assert "ユーザー" in svg and "サーバー" in svg and "リクエスト" in svg
