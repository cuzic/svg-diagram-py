"""End-to-end tests for Diagram.pyramid()/.curve()/.status()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_pyramid_renders_all_layers():
    d = Diagram(width=600, height=300)
    d.pyramid(["基礎", "応用", "発展"], x=50, y=20, width=400)
    svg = d.render_svg()
    _ok(svg)
    assert svg.count("<polygon") == 3
    assert "基礎" in svg and "応用" in svg and "発展" in svg


def test_pyramid_requires_at_least_two_layers():
    d = Diagram(width=600, height=300)
    try:
        d.pyramid(["one"], x=0, y=0, width=400)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_curve_renders_axis_and_points():
    d = Diagram(width=600, height=300)
    d.curve([{"y": 0.9}, {"y": 0.5}, {"y": 0.1}], x=50, y=20, width=400, height=150)
    svg = d.render_svg()
    _ok(svg)
    assert svg.count("<circle") == 3


def test_status_renders_dashed_pill():
    d = Diagram(width=600, height=300)
    d.status("draft", x=20, y=20, width=90)
    svg = d.render_svg()
    _ok(svg)
    assert 'data-status="draft"' in svg
    assert "draft" in svg
