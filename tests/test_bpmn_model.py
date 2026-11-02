"""End-to-end tests for Diagram.bpmn()."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _ok(svg: str) -> None:
    minidom.parseString(svg)


def test_bpmn_renders():
    d = Diagram(width=900, height=300)
    d.bpmn(
        [{"id": "sales", "label": "営業"}, {"id": "ops", "label": "業務"}],
        [
            {"id": "s1", "lane": "sales", "kind": "start"},
            {"id": "t1", "lane": "sales", "label": "見積作成"},
            {"id": "t2", "lane": "ops", "label": "発注処理"},
            {"id": "e1", "lane": "ops", "kind": "end"},
        ],
        [
            {"from": "s1", "to": "t1"},
            {"from": "t1", "to": "t2", "label": "承認", "line": "dashed"},
            {"from": "t2", "to": "e1"},
        ],
        x=0, y=0, width=900,
    )
    svg = d.render_svg()
    _ok(svg)
    assert "見積作成" in svg and "発注処理" in svg


def test_bpmn_fit_shrink_renders():
    d = Diagram(width=460, height=300)
    d.bpmn(
        [{"id": "sales", "label": "営業"}, {"id": "ops", "label": "業務"}],
        [
            {"id": "s1", "lane": "sales", "kind": "start"},
            {"id": "t1", "lane": "sales", "label": "見積作成"},
            {"id": "g1", "lane": "sales", "kind": "xor", "label": "承認?"},
            {"id": "t2", "lane": "ops", "label": "発注処理"},
            {"id": "e1", "lane": "ops", "kind": "end"},
        ],
        [
            {"from": "s1", "to": "t1"},
            {"from": "t1", "to": "g1"},
            {"from": "g1", "to": "t2", "label": "承認"},
            {"from": "t2", "to": "e1"},
        ],
        x=0, y=0, width=460, fit="shrink",
    )
    svg = d.render_svg()
    _ok(svg)
