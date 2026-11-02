"""End-to-end tests for Diagram.fault_tree()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_fault_tree_renders():
    d = Diagram(width=800, height=500)
    d.fault_tree(
        {
            "label": "サービス停止", "gate": "or",
            "children": [
                {"label": "DB障害", "kind": "basic", "p": 0.01},
                {"label": "ネットワーク障害", "kind": "basic", "p": 0.02},
            ],
        },
        x=0, y=0, width=800,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "サービス停止" in svg and "DB障害" in svg


def test_fault_tree_quant_and_cut_sets_render():
    d = Diagram(width=800, height=500)
    d.fault_tree(
        {
            "label": "サービス停止", "gate": "or",
            "children": [
                {"label": "DB障害", "kind": "basic", "p": 0.01},
                {"label": "ネットワーク障害", "kind": "basic", "p": 0.02},
            ],
        },
        x=0, y=0, width=800, quant=True, cut_sets=True,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "頂上事象の確率" in svg
