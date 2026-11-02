"""Golden-master tests for states_band()/flowchart_band()/layout_states_band()/
render_states() against Node's stateDiagram()/flowchart()/layoutStatesBand()/renderStates()
(all exported — live-tested via the shared dummy width function, same technique as
test_bpmn.py). Depends on layered_route.py (layered_attempt), fit_width.py (plan_fit),
flow_nodes.py (diamond/pill shapes) and verify_base.py (density-compact fallback)."""

from __future__ import annotations

import pytest

from svg_diagram.states import flowchart_band, layout_states_band, render_states, states_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


SIMPLE_STATES = [{"id": "idle", "label": "待機"}, {"id": "run", "label": "実行中"}, {"id": "done", "label": "完了", "final": True}]
SIMPLE_TRANSITIONS = [
    {"from": "idle", "to": "run", "label": "開始"},
    {"from": "run", "to": "idle", "label": "中止"},
    {"from": "run", "to": "done"},
]

# a self-loop with a label, a circle state, and a tone
LOOP_STATES = [{"id": "start", "label": "開始", "shape": "circle"}, {"id": "work", "label": "作業中", "tone": "accent"}]
LOOP_TRANSITIONS = [{"from": "start", "to": "work"}, {"from": "work", "to": "work", "label": "retry"}]

# a flowchart: decision (diamond) + terminator (pill) + Yes/No labels, with a return to the decision (returns: outer by default)
FLOW_NODES = [
    {"id": "s", "kind": "terminator", "label": "相談"},
    {"id": "q", "kind": "decision", "label": "自分で答えられる？"},
    {"id": "a", "label": "回答する"},
    {"id": "e", "kind": "terminator", "label": "終了"},
]
FLOW_EDGES = [
    {"from": "s", "to": "q"},
    {"from": "q", "to": "a", "label": "Yes"},
    {"from": "q", "to": "s", "label": "No"},
    {"from": "a", "to": "e"},
]

LAYOUT_CASES = [
    {"id": "simple-down", "states": SIMPLE_STATES, "transitions": SIMPLE_TRANSITIONS, "opts": {"initial": "idle"}, "w": 600},
    {"id": "simple-dir-right", "states": SIMPLE_STATES, "transitions": SIMPLE_TRANSITIONS, "opts": {"initial": "idle", "dir": "right"}, "w": 900},
    {"id": "simple-dir-auto", "states": SIMPLE_STATES, "transitions": SIMPLE_TRANSITIONS, "opts": {"initial": "idle", "dir": "auto"}, "w": 900},
    {"id": "loop-circle-tone-right", "states": LOOP_STATES, "transitions": LOOP_TRANSITIONS, "opts": {"dir": "right"}, "w": 700},
    {"id": "loop-circle-tone-down", "states": LOOP_STATES, "transitions": LOOP_TRANSITIONS, "opts": {}, "w": 500},
    {"id": "flowchart-decision-terminator", "states": FLOW_NODES, "transitions": FLOW_EDGES, "opts": {}, "w": 900, "dsl": "flowchart"},
    {"id": "flowchart-returns-inline", "states": FLOW_NODES, "transitions": FLOW_EDGES, "opts": {"returns": "inline"}, "w": 900, "dsl": "flowchart"},
    {"id": "straighten-false", "states": SIMPLE_STATES, "transitions": SIMPLE_TRANSITIONS, "opts": {"initial": "idle", "straighten": False}, "w": 600},
    {"id": "with-id", "states": SIMPLE_STATES, "transitions": SIMPLE_TRANSITIONS, "opts": {"id": "diag1"}, "w": 600},
    {"id": "max-node-w", "states": SIMPLE_STATES, "transitions": SIMPLE_TRANSITIONS, "opts": {"maxNodeW": 100}, "w": 600},
    {"id": "density-compact", "states": SIMPLE_STATES, "transitions": SIMPLE_TRANSITIONS, "opts": {"initial": "idle"}, "w": 600, "space": 0.75},
]


def _build_band(case: dict) -> dict:
    opts = case["opts"]
    if case.get("dsl") == "flowchart":
        return flowchart_band(case["states"], case["transitions"], dir=opts.get("dir"), max_node_w=opts.get("maxNodeW"), returns=opts.get("returns"), straighten=opts.get("straighten"), id=opts.get("id"))
    return states_band(case["states"], case["transitions"], dir=opts.get("dir"), initial=opts.get("initial"), max_node_w=opts.get("maxNodeW"), returns=opts.get("returns"), straighten=opts.get("straighten"), id=opts.get("id"))


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_layout_states_band_matches_node(node_golden, case):
    req: dict = {"kind": "layoutStatesBand", "states": case["states"], "transitions": case["transitions"], "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]}
    if case.get("dsl"):
        req["dsl"] = case["dsl"]
    if case.get("space") is not None:
        req["space"] = case["space"]
    node_result = node_golden.call(req)
    band = _build_band(case)
    env = {"wrap": "phrase", "keepWords": False}
    if case.get("space") is not None:
        env["space"] = case["space"]
    py_result = layout_states_band(band, 0, 0, case["w"], _width_of, ROLES, env)
    assert py_result == node_result


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_render_states_matches_node(node_golden, case):
    band = _build_band(case)
    env = {"wrap": "phrase", "keepWords": False}
    if case.get("space") is not None:
        env["space"] = case["space"]
    laid = layout_states_band(band, 0, 0, case["w"], _width_of, ROLES, env)
    node_result = node_golden.call({"kind": "renderStates", "band": laid})
    py_result = render_states(laid)
    assert py_result == node_result


def test_states_rejects_no_states():
    with pytest.raises(ValueError):
        states_band([], [])


def test_states_rejects_bad_dir():
    with pytest.raises(ValueError):
        states_band(SIMPLE_STATES, [], dir="up")


def test_states_rejects_duplicate_id():
    with pytest.raises(ValueError):
        band = states_band([{"id": "a", "label": "x"}, {"id": "a", "label": "y"}], [])
        layout_states_band(band, 0, 0, 500, _width_of, ROLES, {"wrap": "phrase", "keepWords": False})


def test_states_rejects_missing_label():
    with pytest.raises(ValueError):
        band = states_band([{"id": "a"}], [])
        layout_states_band(band, 0, 0, 500, _width_of, ROLES, {"wrap": "phrase", "keepWords": False})


def test_states_rejects_unknown_transition_target():
    with pytest.raises(ValueError):
        band = states_band([{"id": "a", "label": "x"}], [{"from": "a", "to": "nope"}])
        layout_states_band(band, 0, 0, 500, _width_of, ROLES, {"wrap": "phrase", "keepWords": False})


def test_states_rejects_diamond_self_loop():
    with pytest.raises(ValueError):
        states_band([{"id": "a", "label": "x", "shape": "diamond"}], [{"from": "a", "to": "a"}])


def test_states_rejects_diamond_final():
    with pytest.raises(ValueError):
        states_band([{"id": "a", "label": "x", "shape": "diamond", "final": True}], [])


def test_flowchart_rejects_unknown_node_option():
    with pytest.raises(ValueError):
        flowchart_band([{"id": "a", "label": "x", "bogus": True}], [])


def test_flowchart_rejects_bad_kind():
    with pytest.raises(ValueError):
        flowchart_band([{"id": "a", "label": "x", "kind": "nope"}], [])


def test_states_too_narrow_raises_fit_error():
    band = states_band(SIMPLE_STATES, SIMPLE_TRANSITIONS, dir="right")
    with pytest.raises(ValueError):
        layout_states_band(band, 0, 0, 20, _width_of, ROLES, {"wrap": "phrase", "keepWords": False})
