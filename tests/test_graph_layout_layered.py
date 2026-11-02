"""Golden-master tests for graph_layout.py's layout_layered()/break_cycles() against Node's
layoutLayered()/breakCycles() (lib/graph-layout.ts, both exported — live-tested via emit_cli.ts).

This is the shared "layered routing" engine behind states()/classes()/bpmn()/cause()/pert()/
causalLoop()/dependencyNetwork() (see py/BANDS.md's Tier 3 note): longest-path layering,
barycentre crossing reduction, and relax/Brandes-Köpf coordinate assignment. No text/font
dependency — callers pre-measure each node's {w, h}."""

from __future__ import annotations

import pytest

from svg_diagram.graph_layout import break_cycles, layout_layered


def _n(*ids: str, w: float = 40, h: float = 20) -> list[dict]:
    return [{"id": i, "size": {"w": w, "h": h}} for i in ids]


def _e(*pairs: tuple[str, str]) -> list[dict]:
    return [{"from": a, "to": b} for a, b in pairs]


# A small acyclic funnel/branch graph: a -> b,c ; b,c -> d (crossing reduction exercised)
BRANCHY = (_n("a", "b", "c", "d"), _e(("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")))
# A longer chain with a crossing in the middle layer
CROSSED = (
    _n("a1", "a2", "b1", "b2", "c1", "c2"),
    _e(("a1", "b2"), ("a2", "b1"), ("b1", "c2"), ("b2", "c1")),
)
# A 3-cycle: one edge must be reversed
CYCLE3 = (_n("a", "b", "c"), _e(("a", "b"), ("b", "c"), ("c", "a")))
# Self-loop plus a normal edge
SELF_LOOP = (_n("a", "b"), _e(("a", "a"), ("a", "b")))
# A diamond with one long edge that skips a layer (needs a dummy chain)
SKIP_LAYER = (_n("a", "b", "c", "d"), _e(("a", "b"), ("b", "c"), ("c", "d"), ("a", "d")))
# A long feedback cycle: d -> a (declared back) closes it and skips 2+ layers, for outer lanes
CYCLE_LONG = (_n("a", "b", "c", "d"), _e(("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")))
# Two disconnected components
DISCONNECTED = (_n("a", "b", "c", "d"), _e(("a", "b"), ("c", "d")))
# Fan-in/fan-out wide layer, for tighten/alap
FUNNEL = (
    _n("in1", "in2", "in3", "mid", "out"),
    _e(("in1", "mid"), ("in2", "mid"), ("in3", "mid"), ("mid", "out")),
)
# A node with only outgoing edges (candidate for tighten) plus an unrelated chain
LOOSE_SOURCE = (_n("x", "a", "b"), _e(("x", "b"), ("a", "b")))

LAYOUT_CASES = [
    {"id": "branchy-right", "nodes": BRANCHY[0], "edges": BRANCHY[1], "opts": {}},
    {"id": "branchy-down", "nodes": BRANCHY[0], "edges": BRANCHY[1], "opts": {"dir": "down"}},
    {"id": "crossed-default-sweeps", "nodes": CROSSED[0], "edges": CROSSED[1], "opts": {}},
    {"id": "crossed-transpose", "nodes": CROSSED[0], "edges": CROSSED[1], "opts": {"transpose": True}},
    {"id": "crossed-zero-sweeps", "nodes": CROSSED[0], "edges": CROSSED[1], "opts": {"sweeps": 0}},
    {"id": "cycle3-default", "nodes": CYCLE3[0], "edges": CYCLE3[1], "opts": {}},
    {"id": "cycle3-declared-back", "nodes": CYCLE3[0], "edges": CYCLE3[1], "opts": {"back": [2]}},
    {"id": "cycle3-start", "nodes": CYCLE3[0], "edges": CYCLE3[1], "opts": {"start": ["b"]}},
    {"id": "self-loop", "nodes": SELF_LOOP[0], "edges": SELF_LOOP[1], "opts": {}},
    {"id": "skip-layer", "nodes": SKIP_LAYER[0], "edges": SKIP_LAYER[1], "opts": {}},
    {"id": "skip-layer-bk", "nodes": SKIP_LAYER[0], "edges": SKIP_LAYER[1], "opts": {"coord": "bk"}},
    {"id": "cycle-long-outer-all", "nodes": CYCLE_LONG[0], "edges": CYCLE_LONG[1], "opts": {"back": [3], "outer": {"which": "all", "gap": 10, "step": 6}}},
    {"id": "cycle-long-outer-near", "nodes": CYCLE_LONG[0], "edges": CYCLE_LONG[1], "opts": {"back": [3], "outer": {"which": "declared", "gap": 10, "step": 6, "side": "near"}}},
    {"id": "cycle-long-outer-low", "nodes": CYCLE_LONG[0], "edges": CYCLE_LONG[1], "opts": {"back": [3], "outer": {"which": "all", "gap": 10, "step": 6, "side": "low"}}},
    {"id": "disconnected", "nodes": DISCONNECTED[0], "edges": DISCONNECTED[1], "opts": {}},
    {"id": "disconnected-bk", "nodes": DISCONNECTED[0], "edges": DISCONNECTED[1], "opts": {"coord": "bk"}},
    {"id": "funnel-plain", "nodes": FUNNEL[0], "edges": FUNNEL[1], "opts": {}},
    {"id": "funnel-bk", "nodes": FUNNEL[0], "edges": FUNNEL[1], "opts": {"coord": "bk"}},
    {"id": "loose-source-tighten", "nodes": LOOSE_SOURCE[0], "edges": LOOSE_SOURCE[1], "opts": {"tighten": True}},
    {"id": "loose-source-no-tighten", "nodes": LOOSE_SOURCE[0], "edges": LOOSE_SOURCE[1], "opts": {"tighten": False}},
    {"id": "funnel-alap", "nodes": FUNNEL[0], "edges": FUNNEL[1], "opts": {"alap": {"keep": []}}},
    {"id": "funnel-alap-keep-mid", "nodes": FUNNEL[0], "edges": FUNNEL[1], "opts": {"alap": {"keep": ["mid"]}}},
    {"id": "branchy-custom-gap", "nodes": BRANCHY[0], "edges": BRANCHY[1], "opts": {"gap": 10, "levelGap": 60}},
    {
        "id": "wide-layer-fold",
        "nodes": _n("h1", "a", "b", "c", "d", "e", w=60),
        "edges": _e(("h1", "a"), ("h1", "b"), ("h1", "c"), ("h1", "d"), ("h1", "e")),
        "opts": {"fold": 200},
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_layout_layered_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutLayered", "nodes": case["nodes"], "edges": case["edges"], "opts": case["opts"]})
    py_result = layout_layered(case["nodes"], case["edges"], case["opts"])
    assert py_result == node_result


BREAK_CYCLES_CASES = [
    {"id": "acyclic", "nodes": BRANCHY[0], "edges": BRANCHY[1], "declared": [], "start": []},
    {"id": "simple-cycle", "nodes": CYCLE3[0], "edges": CYCLE3[1], "declared": [], "start": []},
    {"id": "simple-cycle-declared", "nodes": CYCLE3[0], "edges": CYCLE3[1], "declared": [2], "start": []},
    {"id": "simple-cycle-start", "nodes": CYCLE3[0], "edges": CYCLE3[1], "declared": [], "start": ["c"]},
    {"id": "self-loop-ignored", "nodes": SELF_LOOP[0], "edges": SELF_LOOP[1], "declared": [], "start": []},
]


@pytest.mark.parametrize("case", BREAK_CYCLES_CASES, ids=lambda c: c["id"])
def test_break_cycles_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "breakCycles", "nodes": case["nodes"], "edges": case["edges"], "declared": case["declared"], "start": case["start"]})
    py_result = sorted(break_cycles(case["nodes"], case["edges"], case["declared"], case["start"]))
    assert py_result == node_result


def test_break_cycles_rejects_bad_back_index():
    with pytest.raises(ValueError):
        break_cycles(CYCLE3[0], CYCLE3[1], [99])


def test_break_cycles_rejects_two_back_edges_on_one_cycle():
    nodes = _n("a", "b", "c")
    edges = _e(("a", "b"), ("b", "c"), ("c", "a"))
    with pytest.raises(ValueError):
        break_cycles(nodes, edges, [1, 2])


def test_break_cycles_rejects_back_edge_that_closes_no_cycle():
    nodes = _n("a", "b", "c")
    edges = _e(("a", "b"), ("b", "c"))
    with pytest.raises(ValueError):
        break_cycles(nodes, edges, [1])


def test_layout_layered_rejects_duplicate_node_id():
    with pytest.raises(ValueError):
        layout_layered(_n("a", "a"), [])


def test_layout_layered_rejects_edge_to_unknown_node():
    with pytest.raises(ValueError):
        layout_layered(_n("a", "b"), _e(("a", "z")))
