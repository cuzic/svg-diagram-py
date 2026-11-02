"""End-to-end tests for Diagram.classes()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_classes_renders():
    d = Diagram(width=700, height=500)
    d.classes(
        [
            {"id": "animal", "name": "Animal", "abstract": True, "methods": ["speak()"]},
            {"id": "dog", "name": "Dog", "attrs": ["name: string"], "methods": ["speak()"]},
        ],
        [{"from": "dog", "to": "animal", "kind": "inherit"}],
        x=0, y=0, width=700,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "Animal" in svg and "Dog" in svg


def test_classes_dir_right_with_relation_label_renders():
    d = Diagram(width=900, height=500)
    d.classes(
        [
            {"id": "order", "name": "Order"},
            {"id": "item", "name": "Item"},
        ],
        [{"from": "order", "to": "item", "kind": "compose", "label": "contains", "toMult": "1..*"}],
        x=0, y=0, width=900, dir="right",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "contains" in svg
