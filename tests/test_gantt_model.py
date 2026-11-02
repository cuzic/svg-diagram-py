"""End-to-end test for Diagram.gantt()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def test_gantt_renders():
    d = Diagram(width=900, height=250)
    d.gantt(
        [
            {"section": "設計"},
            {"label": "要件定義", "id": "req", "start": "2026-01-01", "days": 5},
            {"label": "実装", "start": "2026-01-06", "days": 10, "after": "req"},
            {"label": "リリース", "start": "2026-01-16", "milestone": True},
        ],
        x=0, y=0, width=900, today="2026-01-08",
    )
    svg = d.render_svg()
    minidom.parseString(svg)
    assert "要件定義" in svg and "実装" in svg and "リリース" in svg
    assert svg.count("<rect") >= 4  # bg + section + 2 task bars (+milestone path, not a rect)
