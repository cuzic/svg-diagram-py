"""End-to-end tests for Diagram.regplot()/.residplot()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram

X = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
Y = [2.1, 3.9, 6.2, 7.8, 10.1, 12.3, 13.9, 16.2, 17.8, 20.1]


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_regplot_renders():
    d = Diagram(width=600, height=400)
    d.regplot({"x": X, "y": Y}, x=0, y=0, width=600, opts={"stats": True})
    _ok(d.render_svg())


def test_residplot_renders():
    d = Diagram(width=600, height=400)
    d.residplot({"x": X, "y": Y}, x=0, y=0, width=600)
    _ok(d.render_svg())
