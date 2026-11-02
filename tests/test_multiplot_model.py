"""End-to-end tests for Diagram.hist2d()/.jointplot()/.kde2d()/.pairplot()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram

X = [12, 15, 14, 18, 22, 19, 17, 13, 16, 21]
Y = [5, 8, 7, 11, 14, 10, 9, 6, 9, 13]


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_hist2d_renders():
    d = Diagram(width=600, height=500)
    d.hist2d({"x": X, "y": Y}, x=0, y=0, width=600)
    _ok(d.render_svg())


def test_jointplot_renders():
    d = Diagram(width=600, height=500)
    d.jointplot({"x": X, "y": Y}, x=0, y=0, width=600)
    _ok(d.render_svg())


def test_kde2d_renders():
    d = Diagram(width=600, height=500)
    d.kde2d({"x": X, "y": Y}, x=0, y=0, width=600)
    _ok(d.render_svg())


def test_pairplot_renders():
    d = Diagram(width=600, height=500)
    d.pairplot({"身長": X, "体重": Y}, x=0, y=0, width=600)
    _ok(d.render_svg())
