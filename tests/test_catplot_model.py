"""End-to-end tests for Diagram.catplot()/.boxplot()/.violinplot()/.stripplot()/
.swarmplot()/.pointplot()/.barplot()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram

DATA = {"東京": [3, 7, 8, 5, 9, 2, 6, 7, 8, 5], "大阪": [4, 4, 5, 6, 3, 8, 7, 9, 2, 5]}


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_boxplot_renders():
    d = Diagram(width=600, height=400)
    d.boxplot(DATA, x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert "東京" in svg


def test_violinplot_renders():
    d = Diagram(width=600, height=400)
    d.violinplot(DATA, x=0, y=0, width=600)
    _ok(d.render_svg())


def test_stripplot_and_swarmplot_render():
    d = Diagram(width=600, height=400)
    d.stripplot(DATA, x=0, y=0, width=600)
    d.swarmplot(DATA, x=0, y=200, width=600)
    _ok(d.render_svg())


def test_pointplot_and_barplot_render():
    d = Diagram(width=600, height=400)
    d.pointplot(DATA, x=0, y=0, width=600)
    d.barplot(DATA, x=0, y=200, width=600)
    svg = d.render_svg()
    _ok(svg)


def test_catplot_with_kind_list_renders():
    d = Diagram(width=600, height=400)
    d.catplot(DATA, x=0, y=0, width=600, opts={"kind": ["violin", "strip"]})
    _ok(d.render_svg())
