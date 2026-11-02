"""End-to-end tests for Diagram.heatmap()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_heatmap_renders():
    d = Diagram(width=600, height=250)
    d.heatmap(["1月", "2月"], ["0", "1", "2"], [[100, 62, 48], [100, 58, None]], x=0, y=0, width=600, unit="%", corner="登録月 ＼ 経過月")
    svg = d.render_svg()
    _ok(svg)
    assert "1月" in svg and "凡例" in svg


def test_heatmap_without_scale_or_row_header():
    d = Diagram(width=400, height=200)
    d.heatmap(["A", "B"], ["X", "Y"], [[1, 2], [3, 4]], x=0, y=0, width=400, scale=False, row_header=False)
    svg = d.render_svg()
    _ok(svg)
    assert "凡例" not in svg
