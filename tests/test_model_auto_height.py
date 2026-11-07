"""End-to-end tests for `Diagram(width, height="auto")` (this port's own addition, not a
Node option — see model.py's Diagram docstring) and the `bottom()` every element of
Diagram._elements now implements for it. Python-only, not golden-tested at this level
(same reasoning as test_model_extensions.py)."""

import xml.dom.minidom as minidom

import pytest

from svg_diagram import Diagram


def _svg_height(svg: str) -> float:
    dom = minidom.parseString(svg)  # well-formed
    assert dom.documentElement is not None
    return float(dom.documentElement.getAttribute("height"))


def test_fixed_height_unchanged():
    d = Diagram(400, 200)
    d.box("x", x=0, y=0, width=100, height=50)
    assert _svg_height(d.render_svg()) == 200


def test_auto_height_single_box():
    d = Diagram(400, "auto")
    d.box("x", x=0, y=20, width=100, height=50)
    assert _svg_height(d.render_svg()) == 20 + 50 + 24  # AUTO_HEIGHT_MARGIN


def test_auto_height_picks_the_lowest_regardless_of_add_order():
    d = Diagram(400, "auto")
    d.box("low", x=0, y=300, width=100, height=20)
    d.box("high", x=0, y=10, width=100, height=20)
    assert _svg_height(d.render_svg()) == 300 + 20 + 24


def test_auto_height_empty_diagram_is_just_the_margin():
    d = Diagram(400, "auto")
    assert _svg_height(d.render_svg()) == 24


@pytest.mark.parametrize("bad", ["nope", "AUTO", ""])
def test_invalid_height_string_raises(bad):
    with pytest.raises(ValueError):
        Diagram(400, bad)


def test_non_positive_height_raises():
    with pytest.raises(ValueError):
        Diagram(400, 0)
    with pytest.raises(ValueError):
        Diagram(400, -10)


def test_auto_height_across_element_kinds():
    """One element from each bottom()-implementing family — a wiring smoke test, not a
    geometry check: every `bottom()` must run without raising and the result must exceed
    each element's own y (sanity, not pixel-exactness)."""
    d = Diagram(900, "auto")
    d.caption("見出し", x=0, y=0, width=300)
    d.group(x=0, y=40, width=300, height=60, title="グループ")
    d.banner("バナー", x=0, y=120, width=300, height=50)
    d.legend([{"x": 0, "y": 190, "label": "凡例", "kind": "line"}])
    d.status("状態", x=0, y=230, width=100)
    d.raw(x=0, y=270, width=100, height=30, draw=lambda ctx: "<!-- raw -->")
    d.pyramid(["上", "下"], x=0, y=320, width=200)
    d.tree({"label": "root", "children": [{"label": "a"}, {"label": "b"}]}, x=0, y=500, width=300)
    d.table([{"label": "col"}], [["v"]], x=0, y=700, width=200)
    d.gantt([{"label": "task", "start": "2026-01-01", "days": 3}], x=0, y=800, width=400)
    d.chevron([{"label": "a"}, {"label": "b"}], x=0, y=950, width=300)
    d.bars([{"label": "a", "value": 1}, {"label": "b", "value": 2}], x=0, y=1050, width=300)
    d.heatmap(["r"], ["c"], [[1]], x=0, y=1150, width=200)
    d.plane({"x": {"max": 1}, "y": {"max": 1}, "items": [{"x": 0.5, "y": 0.5, "label": "p"}]}, x=0, y=1250, width=300)
    d.bowtie({"top": "事故", "threats": [{"label": "脅威"}], "consequences": [{"label": "結果"}]}, x=0, y=1400, width=600)
    d.classes([{"id": "A"}], [], x=0, y=1700, width=200)
    d.state_diagram([{"id": "a", "label": "待機"}, {"id": "b", "label": "実行"}], [{"from": "a", "to": "b"}], x=0, y=1850, width=300)
    d.cause_tree([{"id": "x", "label": "原因"}, {"id": "y", "label": "結果"}], [{"from": "x", "to": "y"}], x=0, y=2000, width=300)
    d.swimlane(
        lanes=[{"id": "l1", "label": "レーン"}],
        steps=[{"lane": "l1", "col": 1, "span": 1, "title": "手順"}],
        x=0, y=2200, width=300, cols=1,
    )
    d.wireframe({"t": "text", "text": "画面"}, x=0, y=2400, width=300)
    d.screens([{"title": "画面1", "root": {"t": "text", "text": "A"}}], x=0, y=2900, width=300)

    svg = d.render_svg()
    minidom.parseString(svg)  # well-formed
    h = _svg_height(svg)
    assert h > 2900  # taller than the lowest element's own y: bottom() ran for every kind
