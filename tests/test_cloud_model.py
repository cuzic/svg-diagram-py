"""End-to-end test for Diagram.cloud()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def test_cloud_renders():
    d = Diagram(width=900, height=200)
    d.cloud(
        {"a": "共通の目的を達成する", "b": "品質を保つ", "c": "速度を保つ", "d": "レビューを徹底する", "d2": "レビューを省略する"},
        x=0, y=0, width=900, conflict_label="対立",
    )
    svg = d.render_svg()
    minidom.parseString(svg)
    assert "共通の目的を達成する" in svg
    assert "対立" in svg
    assert svg.count("<rect") == 1 + 5 + 1  # bg + 5 boxes + the conflict-label chip background
