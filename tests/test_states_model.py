"""End-to-end tests for Diagram.state_diagram()/Diagram.flowchart()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_state_diagram_renders():
    d = Diagram(width=600, height=400)
    d.state_diagram(
        [{"id": "idle", "label": "待機"}, {"id": "run", "label": "実行中"}, {"id": "done", "label": "完了", "final": True}],
        [{"from": "idle", "to": "run", "label": "開始"}, {"from": "run", "to": "idle", "label": "中止"}, {"from": "run", "to": "done"}],
        x=0, y=0, width=600, initial="idle",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "待機" in svg and "実行中" in svg


def test_flowchart_renders_decision_and_terminator():
    d = Diagram(width=900, height=400)
    d.flowchart(
        [
            {"id": "s", "kind": "terminator", "label": "相談"},
            {"id": "q", "kind": "decision", "label": "自分で答えられる？"},
            {"id": "a", "label": "回答する"},
        ],
        [{"from": "s", "to": "q"}, {"from": "q", "to": "a", "label": "Yes"}],
        x=0, y=0, width=900,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "Yes" in svg
