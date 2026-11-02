"""End-to-end tests for Diagram.wordart()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_wordart_plain_renders():
    d = Diagram(width=600, height=120)
    d.wordart("タイトル", x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert "タイトル" in svg


def test_wordart_arc_renders():
    d = Diagram(width=600, height=200)
    d.wordart("ARCHED TEXT", x=0, y=0, width=600, arc=30, style="shadow")
    svg = d.render_svg()
    _ok(svg)
    assert "<text" in svg


def test_wordart_vertical_renders():
    d = Diagram(width=200, height=400)
    d.wordart("縦書きの見出し", x=0, y=0, width=200, writing="vertical")
    svg = d.render_svg()
    _ok(svg)
    assert "縦書きの見出し" not in svg  # split across <tspan>/<text> runs, not one run
    assert svg.count("<tspan") > 0 or "<text" in svg


def test_wordart_gradient_and_plate_renders():
    d = Diagram(width=600, height=160)
    d.wordart("セール", x=0, y=0, width=600, gradient={"from": "accent", "to": "danger"}, plate="soft")
    svg = d.render_svg()
    _ok(svg)
    assert "<linearGradient" in svg
    assert "<rect" in svg
