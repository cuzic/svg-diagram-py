"""End-to-end tests for Diagram.pert()/Diagram.dependency_network()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_pert_renders():
    d = Diagram(width=800, height=300)
    d.pert(
        [
            {"id": "a", "label": "設計", "duration": 3},
            {"id": "b", "label": "実装", "duration": 5, "predecessors": ["a"]},
            {"id": "c", "label": "テスト", "duration": 2, "predecessors": ["b"]},
        ],
        x=0, y=0, width=800, unit="日",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "設計" in svg and "実装" in svg


def test_dependency_network_renders():
    d = Diagram(width=800, height=300)
    d.dependency_network(
        [{"id": "a", "label": "Core"}, {"id": "b", "label": "Util"}],
        [{"from": "a", "to": "b", "type": "depends"}],
        x=0, y=0, width=800,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "Core" in svg and "Util" in svg
