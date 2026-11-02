"""End-to-end tests for Diagram.displot()/.histplot()/.kdeplot()/.ecdfplot()/.rugplot()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram

VALUES = [12, 15, 14, 18, 22, 19, 17, 13, 16, 21, 20, 14, 15, 18, 25, 11, 16, 19, 23, 17]


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_histplot_renders():
    d = Diagram(width=600, height=400)
    d.histplot(VALUES, x=0, y=0, width=600)
    _ok(d.render_svg())


def test_kdeplot_renders():
    d = Diagram(width=600, height=400)
    d.kdeplot(VALUES, x=0, y=0, width=600)
    _ok(d.render_svg())


def test_ecdfplot_and_rugplot_render():
    d = Diagram(width=600, height=400)
    d.ecdfplot(VALUES, x=0, y=0, width=600)
    d.rugplot(VALUES, x=0, y=200, width=600)
    _ok(d.render_svg())


def test_displot_with_kind_list_renders():
    d = Diagram(width=600, height=400)
    d.displot(VALUES, x=0, y=0, width=600, opts={"kind": ["hist", "kde", "rug"]})
    _ok(d.render_svg())
