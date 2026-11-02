"""Golden-master tests for fta_band()/layout_fta()/render_fta() against Node's
faultTree()/layoutFta()/renderFta() (all exported — live-tested via the shared dummy
width function, same technique as test_bowtie.py)."""

from __future__ import annotations

import pytest

from svg_diagram.fta import fta_band, layout_fta, render_fta

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


SIMPLE_OR = {
    "label": "サービス停止", "gate": "or",
    "children": [
        {"label": "DB障害", "kind": "basic", "p": 0.01},
        {"label": "ネットワーク障害", "kind": "basic", "p": 0.02},
    ],
}

AND_WITH_HOUSE = {
    "label": "停電による影響", "gate": "and",
    "children": [
        {"label": "停電", "kind": "basic", "p": 0.05},
        {"label": "UPS未設置", "kind": "house", "state": True},
    ],
}

VOTE_GATE = {
    "label": "多重故障", "gate": "vote", "k": 2,
    "children": [
        {"label": "センサーA", "kind": "basic", "p": 0.1},
        {"label": "センサーB", "kind": "basic", "p": 0.1},
        {"label": "センサーC", "kind": "undeveloped"},
    ],
}

INHIBIT_GATE = {
    "label": "誤出荷", "gate": "inhibit",
    "children": [{"label": "ラベル取り違え", "kind": "basic", "p": 0.03}],
    "condition": {"label": "検品スキップ", "kind": "condition", "p": 0.2},
}

NESTED_WITH_REF = {
    "label": "頂上事象", "gate": "or", "id": "top",
    "children": [
        {"label": "原因A", "gate": "and", "children": [
            {"label": "共有事象", "kind": "basic", "id": "shared", "p": 0.04},
            {"label": "単独事象1", "kind": "undeveloped"},
        ]},
        {"label": "原因B", "gate": "and", "children": [
            {"ref": "shared"},
            {"label": "単独事象2", "kind": "basic", "p": 0.07},
        ]},
    ],
}

LAYOUT_CASES = [
    {"root": SIMPLE_OR, "opts": {}, "w": 800},
    {"root": AND_WITH_HOUSE, "opts": {}, "w": 800},
    {"root": VOTE_GATE, "opts": {}, "w": 900},
    {"root": INHIBIT_GATE, "opts": {}, "w": 800},
    {"root": NESTED_WITH_REF, "opts": {"cutSets": True}, "w": 900},
    {"root": SIMPLE_OR, "opts": {"cutSets": True}, "w": 800},
    {"root": SIMPLE_OR, "opts": {"quant": True}, "w": 800},
    {"root": SIMPLE_OR, "opts": {"quant": True, "quantPeriod": "1 年間"}, "w": 800},
    {"root": {"label": "長いイベント名のテストテストテスト" * 2, "gate": "or", "children": [{"label": "A", "kind": "basic", "p": 0.1}, {"label": "B", "kind": "basic", "p": 0.1}]}, "opts": {"maxNodeW": "auto"}, "w": 500},
    {"root": SIMPLE_OR, "opts": {"maxNodeW": 130}, "w": 500},
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["root"]["label"][:16] + str(c["opts"]))
def test_layout_fta_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutFta", "root": case["root"], "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]})
    band = fta_band(case["root"], max_node_w=case["opts"].get("maxNodeW"), cut_sets=case["opts"].get("cutSets"), quant=case["opts"].get("quant"), quant_period=case["opts"].get("quantPeriod"))
    py_result = layout_fta(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    assert py_result == node_result


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["root"]["label"][:16] + str(c["opts"]))
def test_render_fta_matches_node(node_golden, case):
    band = fta_band(case["root"], max_node_w=case["opts"].get("maxNodeW"), cut_sets=case["opts"].get("cutSets"), quant=case["opts"].get("quant"), quant_period=case["opts"].get("quantPeriod"))
    laid = layout_fta(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderFta", "band": laid})
    py_result = render_fta(laid)
    assert py_result == node_result


def test_fta_rejects_missing_gate_on_event():
    with pytest.raises(ValueError):
        fta_band({"label": "x", "kind": "event"})


def test_fta_rejects_bad_vote_k():
    with pytest.raises(ValueError):
        fta_band({"label": "x", "gate": "vote", "k": 5, "children": [{"label": "a", "kind": "basic", "p": 0.1}]})


def test_fta_rejects_unknown_ref():
    with pytest.raises(ValueError):
        fta_band({"label": "x", "gate": "or", "children": [{"ref": "nope"}]})


def test_fta_quant_requires_p_on_every_basic():
    with pytest.raises(ValueError):
        fta_band({"label": "x", "gate": "or", "children": [{"label": "a", "kind": "basic"}]}, quant=True)


def test_fta_cut_sets_marks_single_points_of_failure():
    band = fta_band(SIMPLE_OR, cut_sets=True)
    laid = layout_fta(band, 0, 0, 800, _width_of, ROLES, "phrase")
    assert len(laid["badges"]) == 2
