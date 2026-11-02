"""Golden-master tests for bpmn_band()/layout_bpmn()/render_bpmn() against Node's
bpmn()/layoutBpmn()/renderBpmn() (all exported — live-tested via the shared dummy width
function, same technique as test_bowtie.py/test_fta.py)."""

from __future__ import annotations

import pytest

from svg_diagram.bpmn import bpmn_band, layout_bpmn, render_bpmn

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LANES_2 = [{"id": "sales", "label": "営業"}, {"id": "ops", "label": "業務"}]
NODES_LINEAR = [
    {"id": "s1", "lane": "sales", "kind": "start"},
    {"id": "t1", "lane": "sales", "label": "見積作成"},
    {"id": "g1", "lane": "sales", "kind": "xor", "label": "承認?"},
    {"id": "t2", "lane": "ops", "label": "発注処理"},
    {"id": "e1", "lane": "ops", "kind": "end"},
]
FLOWS_LINEAR = [
    {"from": "s1", "to": "t1"},
    {"from": "t1", "to": "g1"},
    {"from": "g1", "to": "t2", "label": "承認"},
    {"from": "t2", "to": "e1"},
]

# a back edge (loop) within one lane, plus a parallel (and) gateway and a message flow
LANES_1 = [{"id": "ops", "label": "業務"}]
NODES_LOOP = [
    {"id": "s1", "lane": "ops", "kind": "start"},
    {"id": "t1", "lane": "ops", "label": "受付"},
    {"id": "t2", "lane": "ops", "label": "確認", "tone": "accent"},
    {"id": "g1", "lane": "ops", "kind": "and", "label": "分岐"},
    {"id": "t3", "lane": "ops", "label": "処理A"},
    {"id": "t4", "lane": "ops", "label": "処理B", "sub": "並行実行"},
    {"id": "e1", "lane": "ops", "kind": "end"},
]
FLOWS_LOOP = [
    {"from": "s1", "to": "t1"},
    {"from": "t1", "to": "t2"},
    {"from": "t2", "to": "t1", "label": "やり直し", "line": "dashed"},
    {"from": "t2", "to": "g1"},
    {"from": "g1", "to": "t3"},
    {"from": "g1", "to": "t4"},
    {"from": "t3", "to": "e1"},
    {"from": "t4", "to": "e1"},
]

# a self-loop, an inclusive (or) gateway, and a back edge into an earlier column but a later row
NODES_MIXED = [
    {"id": "s1", "lane": "ops", "kind": "start"},
    {"id": "t1", "lane": "ops", "label": "受付"},
    {"id": "g1", "lane": "ops", "kind": "or", "label": "条件"},
    {"id": "t2", "lane": "ops", "label": "再試行対象タスク", "sub": "備考"},
    {"id": "e1", "lane": "ops", "kind": "end"},
]
FLOWS_MIXED = [
    {"from": "s1", "to": "t1"},
    {"from": "t1", "to": "t1"},
    {"from": "t1", "to": "g1"},
    {"from": "g1", "to": "t2"},
    {"from": "t2", "to": "t1"},
    {"from": "t2", "to": "e1"},
]

LAYOUT_CASES = [
    {"id": "linear-two-lanes", "lanes": LANES_2, "nodes": NODES_LINEAR, "flows": FLOWS_LINEAR, "opts": {}, "w": 900},
    {"id": "loop-and-gateway-dashed", "lanes": LANES_1, "nodes": NODES_LOOP, "flows": FLOWS_LOOP, "opts": {}, "w": 1000},
    {"id": "self-loop-or-gateway-back", "lanes": LANES_1, "nodes": NODES_MIXED, "flows": FLOWS_MIXED, "opts": {}, "w": 700},
    {"id": "fit-shrink-narrow", "lanes": LANES_2, "nodes": NODES_LINEAR, "flows": FLOWS_LINEAR, "opts": {"fit": "shrink"}, "w": 460},
    {"id": "with-id", "lanes": LANES_1, "nodes": NODES_LOOP, "flows": FLOWS_LOOP, "opts": {"id": "flow1"}, "w": 1000},
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_layout_bpmn_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutBpmn", "lanes": case["lanes"], "nodes": case["nodes"], "flows": case["flows"], "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]})
    band = bpmn_band(case["lanes"], case["nodes"], case["flows"], fit=case["opts"].get("fit"), id=case["opts"].get("id"))
    py_result = layout_bpmn(band, 0, 0, case["w"], _width_of, ROLES)
    assert py_result == node_result


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_render_bpmn_matches_node(node_golden, case):
    band = bpmn_band(case["lanes"], case["nodes"], case["flows"], fit=case["opts"].get("fit"), id=case["opts"].get("id"))
    laid = layout_bpmn(band, 0, 0, case["w"], _width_of, ROLES)
    node_result = node_golden.call({"kind": "renderBpmn", "band": laid})
    py_result = render_bpmn(laid)
    assert py_result == node_result


def test_bpmn_rejects_no_lanes():
    with pytest.raises(ValueError):
        bpmn_band([], NODES_LINEAR, FLOWS_LINEAR)


def test_bpmn_rejects_no_nodes():
    with pytest.raises(ValueError):
        bpmn_band(LANES_2, [], [])


def test_bpmn_rejects_task_without_label():
    with pytest.raises(ValueError):
        band = bpmn_band(LANES_1, [{"id": "t1", "lane": "ops"}], [])
        layout_bpmn(band, 0, 0, 500, _width_of, ROLES)


def test_bpmn_rejects_unknown_lane():
    with pytest.raises(ValueError):
        band = bpmn_band(LANES_1, [{"id": "t1", "lane": "nope", "label": "x"}], [])
        layout_bpmn(band, 0, 0, 500, _width_of, ROLES)


def test_bpmn_rejects_duplicate_node_id():
    with pytest.raises(ValueError):
        band = bpmn_band(LANES_1, [{"id": "t1", "lane": "ops", "label": "a"}, {"id": "t1", "lane": "ops", "label": "b"}], [])
        layout_bpmn(band, 0, 0, 500, _width_of, ROLES)


def test_bpmn_rejects_flow_into_start():
    with pytest.raises(ValueError):
        band = bpmn_band(LANES_1, [{"id": "s1", "lane": "ops", "kind": "start"}, {"id": "t1", "lane": "ops", "label": "a"}], [{"from": "t1", "to": "s1"}])
        layout_bpmn(band, 0, 0, 500, _width_of, ROLES)


def test_bpmn_rejects_flow_out_of_end():
    with pytest.raises(ValueError):
        band = bpmn_band(LANES_1, [{"id": "e1", "lane": "ops", "kind": "end"}, {"id": "t1", "lane": "ops", "label": "a"}], [{"from": "e1", "to": "t1"}])
        layout_bpmn(band, 0, 0, 500, _width_of, ROLES)


def test_bpmn_rejects_node_icon():
    with pytest.raises(NotImplementedError):
        bpmn_band(LANES_1, [{"id": "t1", "lane": "ops", "label": "a", "icon": "check"}], [])


def test_bpmn_rejects_fit_not_shrink():
    with pytest.raises(ValueError):
        bpmn_band(LANES_1, [{"id": "t1", "lane": "ops", "label": "a"}], [], fit="other")


def test_bpmn_too_narrow_without_shrink_raises():
    band = bpmn_band(LANES_2, NODES_LINEAR, FLOWS_LINEAR)
    with pytest.raises(ValueError):
        layout_bpmn(band, 0, 0, 100, _width_of, ROLES)
