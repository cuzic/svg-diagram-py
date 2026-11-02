"""Golden-master tests for pert_band()/dependency_band()/layout_chart()/render_chart()
against Node's pert()/dependencyNetwork()/layoutChart()/renderChart() (all exported —
live-tested via the shared dummy width function, same technique as test_combo.py).
causalLoop() is out of this port's scope (see semnet.py's module docstring)."""

from __future__ import annotations

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.semnet import dependency_band, pert_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


TASKS_LINEAR = [
    {"id": "a", "label": "設計", "duration": 3},
    {"id": "b", "label": "実装", "duration": 5, "predecessors": ["a"]},
    {"id": "c", "label": "テスト", "duration": 2, "predecessors": ["b"]},
]
# a fan-in/fan-out with a non-critical slack path, to exercise the critical-path/slack math beyond a trivial chain
TASKS_DIAMOND = [
    {"id": "a", "label": "計画", "duration": 2},
    {"id": "b", "label": "設計A", "duration": 5, "predecessors": ["a"]},
    {"id": "c", "label": "設計B", "duration": 2, "predecessors": ["a"]},
    {"id": "d", "label": "統合", "duration": 3, "predecessors": ["b", "c"]},
]

PERT_CASES = [
    {"id": "linear-default", "tasks": TASKS_LINEAR, "opts": {}, "w": 800},
    {"id": "linear-compact-unit", "tasks": TASKS_LINEAR, "opts": {"unit": "日", "compact": True}, "w": 700},
    {"id": "diamond-direction-tb", "tasks": TASKS_DIAMOND, "opts": {"direction": "TB"}, "w": 600},
    {"id": "diamond-straighten-false", "tasks": TASKS_DIAMOND, "opts": {"straighten": False}, "w": 900},
]


@pytest.mark.parametrize("case", PERT_CASES, ids=lambda c: c["id"])
def test_layout_pert_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "pert", "tasks": case["tasks"], "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]})
    opts = case["opts"]
    band = pert_band(case["tasks"], direction=opts.get("direction"), unit=opts.get("unit"), compact=opts.get("compact"), straighten=opts.get("straighten"))
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted", "edges"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", PERT_CASES, ids=lambda c: c["id"])
def test_render_pert_matches_node(node_golden, case):
    opts = case["opts"]
    band = pert_band(case["tasks"], direction=opts.get("direction"), unit=opts.get("unit"), compact=opts.get("compact"), straighten=opts.get("straighten"))
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


DEP_NODES = [{"id": "a", "label": "Core", "kind": "service"}, {"id": "b", "label": "Util"}, {"id": "c", "label": "DB", "kind": "infra"}]
DEP_EDGES = [
    {"from": "a", "to": "b", "type": "depends"},
    {"from": "a", "to": "c", "type": "uses", "weight": 3, "label": "query"},
    {"from": "b", "to": "c", "type": "blocks"},
    {"from": "c", "to": "a", "type": "relates"},
]

DEPENDENCY_CASES = [
    {"id": "default", "nodes": DEP_NODES, "edges": DEP_EDGES, "opts": {}, "w": 800},
    {"id": "direction-tb", "nodes": DEP_NODES, "edges": DEP_EDGES, "opts": {"direction": "TB"}, "w": 600},
    {"id": "custom-labels", "nodes": DEP_NODES, "edges": DEP_EDGES, "opts": {"nodeKinds": {"service": "サービス", "infra": "基盤"}, "edgeTypes": {"depends": "依存", "uses": "利用", "blocks": "ブロック", "relates": "関連"}}, "w": 800},
]


@pytest.mark.parametrize("case", DEPENDENCY_CASES, ids=lambda c: c["id"])
def test_layout_dependency_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "dependency", "nodes": case["nodes"], "edges": case["edges"], "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]})
    opts = case["opts"]
    band = dependency_band(case["nodes"], case["edges"], direction=opts.get("direction"), node_kinds=opts.get("nodeKinds"), edge_types=opts.get("edgeTypes"))
    py_result = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "segs", "anchors", "omitted", "edges"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", DEPENDENCY_CASES, ids=lambda c: c["id"])
def test_render_dependency_matches_node(node_golden, case):
    opts = case["opts"]
    band = dependency_band(case["nodes"], case["edges"], direction=opts.get("direction"), node_kinds=opts.get("nodeKinds"), edge_types=opts.get("edgeTypes"))
    laid = layout_chart(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


def test_pert_rejects_empty_tasks():
    with pytest.raises(ValueError):
        pert_band([])


def test_pert_rejects_cycle():
    with pytest.raises(ValueError):
        pert_band([{"id": "a", "label": "A", "duration": 1, "predecessors": ["b"]}, {"id": "b", "label": "B", "duration": 1, "predecessors": ["a"]}])


def test_pert_rejects_unknown_predecessor():
    with pytest.raises(ValueError):
        pert_band([{"id": "a", "label": "A", "duration": 1, "predecessors": ["nope"]}])


def test_dependency_rejects_empty_nodes():
    with pytest.raises(ValueError):
        dependency_band([], [])


def test_dependency_rejects_unknown_edge_target():
    with pytest.raises(ValueError):
        dependency_band([{"id": "a", "label": "A"}], [{"from": "a", "to": "nope", "type": "depends"}])


def test_dependency_rejects_negative_weight():
    with pytest.raises(ValueError):
        dependency_band([{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], [{"from": "a", "to": "b", "type": "depends", "weight": -1}])
