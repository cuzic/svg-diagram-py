"""End-to-end tests for Diagram.stacked_bars()/.mekko()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_stacked_bars_renders():
    d = Diagram(width=500, height=400)
    d.stacked_bars(
        [{"label": "2023", "parts": [{"label": "国内", "value": 60}, {"label": "海外", "value": 40}]}, {"label": "2024", "parts": [{"label": "国内", "value": 55}, {"label": "海外", "value": 65}]}],
        x=0,
        y=0,
        width=500,
        unit="億円",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "国内" in svg


def test_stacked_bars_percent_renders():
    d = Diagram(width=400, height=400)
    d.stacked_bars([{"label": "A", "parts": [{"label": "x", "value": 3}, {"label": "y", "value": 7}]}, {"label": "B", "parts": [{"label": "x", "value": 5}, {"label": "y", "value": 5}]}], x=0, y=0, width=400, percent=True)
    svg = d.render_svg()
    _ok(svg)
    assert "%" in svg


def test_mekko_renders():
    d = Diagram(width=400, height=400)
    d.mekko([{"label": "A社", "parts": [{"label": "製品", "value": 70}, {"label": "保守", "value": 30}]}, {"label": "B社", "parts": [{"label": "製品", "value": 40}, {"label": "保守", "value": 20}]}], x=0, y=0, width=400, unit="億円")
    svg = d.render_svg()
    _ok(svg)
    assert "A社" in svg
