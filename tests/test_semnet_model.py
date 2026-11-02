"""End-to-end tests for Diagram.pert()/Diagram.causal_loop()/Diagram.dependency_network()."""

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


def test_causal_loop_renders_layered():
    d = Diagram(width=900, height=300)
    d.causal_loop(
        [{"id": "a", "label": "流入"}, {"id": "b", "label": "在庫"}, {"id": "c", "label": "流出"}],
        [{"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "c", "polarity": "+"}, {"from": "c", "to": "a", "polarity": "-"}],
        x=0, y=0, width=900,
        interventions=[{"id": "iv1", "label": "施策1", "to": "b", "polarity": "same"}],
    )
    svg = d.render_svg()
    _ok(svg)
    assert "流入" in svg and "施策1" in svg


def test_causal_loop_renders_ring():
    d = Diagram(width=900, height=400)
    d.causal_loop(
        [{"id": "a", "label": "受注"}, {"id": "b", "label": "生産"}, {"id": "c", "label": "在庫"}, {"id": "d", "label": "配送"}],
        [{"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "c", "polarity": "+"}, {"from": "c", "to": "d", "polarity": "+"}, {"from": "d", "to": "a", "polarity": "+"}],
        x=0, y=0, width=900, layout="ring",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "受注" in svg


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
