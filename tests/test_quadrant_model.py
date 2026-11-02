"""End-to-end tests for Diagram.quadrant()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_quadrant_preset_renders():
    d = Diagram(width=700, height=500)
    d.quadrant({"preset": "bcg", "items": [{"label": "製品A", "cell": [0, 0]}, {"label": "製品B", "at": [0.8, 0.9]}]}, x=0, y=0, width=700)
    svg = d.render_svg()
    _ok(svg)
    assert "製品A" in svg and "花形" in svg


def test_quadrant_custom_axes_with_arrow_and_sizes_renders():
    d = Diagram(width=700, height=500)
    d.quadrant(
        {
            "x": {"title": "価格", "low": "安い", "high": "高い"}, "y": {"title": "品質", "low": "低い", "high": "高い"},
            "items": [{"id": "a", "label": "自社", "at": [0.5, 0.5], "size": 40}, {"id": "b", "label": "競合", "at": [0.7, 0.3], "size": 80}],
            "arrows": [{"from": "a", "to": "b", "label": "追い上げ"}], "sizeTitle": "売上", "sizeUnit": "億円",
        },
        x=0, y=0, width=700,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "自社" in svg and "追い上げ" in svg


def test_quadrant_crosshair_with_regions_renders():
    d = Diagram(width=700, height=500)
    d.quadrant(
        {"preset": "positioning", "items": [{"label": "A", "at": [0.2, 0.2]}], "regions": [{"title": "フロー", "points": [[0, 0], [1, 0], [1, 1], [0, 1]]}]},
        x=0, y=0, width=700,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "フロー" in svg
