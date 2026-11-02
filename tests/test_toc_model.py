"""End-to-end tests for Diagram.cause_tree()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_cause_tree_renders_crt_with_and():
    d = Diagram(width=900, height=400)
    d.cause_tree(
        [
            {"id": "a", "label": "納期遅れ", "role": "ude"},
            {"id": "b", "label": "並行作業が多い"},
            {"id": "c", "label": "切替ロス"},
            {"id": "d", "label": "根本原因", "role": "root"},
        ],
        [{"from": ["b", "c"], "to": "a"}, {"from": "d", "to": "b"}, {"from": "d", "to": "c"}],
        x=0, y=0, width=900, tree="crt", core_driver=True,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "納期遅れ" in svg and "根本原因" in svg


def test_cause_tree_renders_with_back_edge():
    d = Diagram(width=900, height=400)
    d.cause_tree(
        [{"id": "a", "label": "在庫増加", "role": "ude"}, {"id": "b", "label": "生産遅延"}, {"id": "c", "label": "発注増加", "role": "root"}],
        [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "c", "to": "a", "back": True}],
        x=0, y=0, width=900, tree="crt",
    )
    svg = d.render_svg()
    _ok(svg)
    assert "在庫増加" in svg
