"""End-to-end tests for Diagram.combo()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_combo_renders():
    d = Diagram(width=600, height=400)
    d.combo(
        ["1月", "2月", "3月", "4月"],
        [{"label": "売上", "type": "bar", "values": [100, 120, 90, 140]}, {"label": "利益率", "type": "line", "values": [10, 12, 8, 15]}],
        x=0,
        y=0,
        width=600,
        y_axis={"unit": "億円"},
        y2_axis={"unit": "%"},
    )
    svg = d.render_svg()
    _ok(svg)
    assert "売上" in svg and "利益率" in svg


def test_combo_stacked_renders():
    d = Diagram(width=500, height=400)
    d.combo(["A", "B", "C"], [{"label": "X", "type": "bar", "values": [10, 20, 15]}, {"label": "Y", "type": "bar", "values": [5, 10, 8]}], x=0, y=0, width=500, stack=True)
    svg = d.render_svg()
    _ok(svg)
    assert "X" in svg and "Y" in svg
