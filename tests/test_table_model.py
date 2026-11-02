"""End-to-end test for Diagram.table()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def test_table_renders():
    d = Diagram(width=600, height=200)
    d.table(
        [{"label": "項目", "flex": 1}, {"label": "値", "flex": 1}],
        [["速度", "速い"], ["コスト", "安い"], [{"text": "品質", "bold": True}, {"mark": "best"}]],
        x=0, y=0, width=600, title="比較表",
    )
    svg = d.render_svg()
    minidom.parseString(svg)
    assert "比較表" in svg and "速度" in svg and "◎" in svg
