"""End-to-end tests for Diagram.people()/.dots()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_people_renders_icon_grid():
    d = Diagram(width=600, height=300)
    d.people(total=10, count=6, x=20, y=20, width=300, cols=5)
    svg = d.render_svg()
    _ok(svg)
    assert svg.count("<path d=\"M12 4a4") == 10


def test_people_with_side_label():
    d = Diagram(width=600, height=300)
    d.people(total=10, count=6, x=20, y=20, width=300, cols=5, side={"value": "60%", "label": "完了率"})
    svg = d.render_svg()
    _ok(svg)
    assert "60%" in svg and "完了率" in svg


def test_dots_renders_axis_and_dots():
    d = Diagram(width=600, height=200)
    d.dots([{"at": 10}, {"at": 50}, {"at": 90}], x=20, y=20, width=400)
    svg = d.render_svg()
    _ok(svg)
    assert "<line" in svg
    assert svg.count("<circle") == 3


def test_dots_with_zones_and_labels():
    d = Diagram(width=600, height=200)
    d.dots([{"at": 10}, {"at": 90}], x=20, y=20, width=400, zones=[{"from": 0, "to": 30, "tone": "muted", "label": "低"}], low_label="少", high_label="多")
    svg = d.render_svg()
    _ok(svg)
    assert "少" in svg and "多" in svg and "低" in svg
