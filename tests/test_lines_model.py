"""End-to-end tests for Diagram.lines()/.burndown()/.burnup()/.strategy_canvas()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_lines_renders():
    d = Diagram(width=600, height=400)
    d.lines(
        [{"label": "売上", "values": [10, 20, 15, 30]}, {"label": "目標", "values": [10, 15, 20, 25], "ideal": True}],
        x=0,
        y=0,
        width=600,
        opts={"x": {"categories": ["1Q", "2Q", "3Q", "4Q"]}, "target": {"at": 25, "label": "目標"}},
    )
    svg = d.render_svg()
    _ok(svg)
    assert "売上" in svg


def test_burndown_renders():
    d = Diagram(width=600, height=400)
    d.burndown({"total": 100, "days": 10, "actual": [100, 90, 80, None, None, None, None, None, None, None, None]}, x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert "理想" in svg and "実績" in svg


def test_burnup_renders():
    d = Diagram(width=600, height=400)
    d.burnup({"scope": 50, "days": 10, "done": [0, 5, 10, None, None, None, None, None, None, None, None]}, x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert "スコープ" in svg and "完了" in svg


def test_strategy_canvas_renders():
    d = Diagram(width=600, height=400)
    d.strategy_canvas(["価格", "品質", "速度"], [{"label": "自社", "values": [4, 3, 5]}, {"label": "競合", "values": [2, 5, 3]}], x=0, y=0, width=600)
    svg = d.render_svg()
    _ok(svg)
    assert "価格" in svg and "自社" in svg
