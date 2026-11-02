"""Golden-master tests for layered_route.py's small pure functions (Phase 1 of the
layered-route.ts port): stub_of/lane_step_of/gap_for/elbows/corridor_load/layout_with_lanes
(all exported in Node — live-tested via emit_cli.ts). routeOnce/routeLayered/layeredAttempt
are tested separately (test_layered_route_route.py / test_layered_route_attempt.py)."""

from __future__ import annotations

import pytest

from svg_diagram.graph_layout import layout_layered
from svg_diagram.layered_route import corridor_load, elbows, gap_for, lane_step_of, layout_with_lanes, stub_of


def _p(x: float, y: float) -> dict:
    return {"x": x, "y": y}


# space=0.75 (density:'compact', ADR 0036) is the real-world case where js_round's
# round-half-up vs Python round()'s banker's rounding would silently diverge: stub_of(0.75) =
# js_round(18*0.75) = js_round(13.5) = 14, lane_step_of(0.75) = js_round(14*0.75) =
# js_round(10.5) = 11 (Python round() would give 13 and 10 respectively).
@pytest.mark.parametrize("space", [1, 0.75, 1.5, 2])
def test_stub_of_matches_node(node_golden, space):
    assert stub_of(space) == node_golden.call({"kind": "stubOf", "space": space})


@pytest.mark.parametrize("space", [1, 0.75, 1.5, 2])
def test_lane_step_of_matches_node(node_golden, space):
    assert lane_step_of(space) == node_golden.call({"kind": "laneStepOf", "space": space})


GAP_FOR_CASES = [
    {"n": 1, "chip": 0, "space": 1},
    {"n": 3, "chip": 0, "space": 1},
    {"n": 5, "chip": 40, "space": 1},
    {"n": 3, "chip": 0, "space": 0.75},
    {"n": 1, "chip": 100, "space": 0.75},
]


@pytest.mark.parametrize("case", GAP_FOR_CASES, ids=lambda c: f"n{c['n']}-chip{c['chip']}-sp{c['space']}")
def test_gap_for_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "gapFor", **case})
    assert gap_for(case["n"], case["chip"], case["space"]) == node_result


ELBOWS_CASES = [
    {"id": "two-points-level", "pts": [_p(0, 0), _p(100, 0)]},
    {"id": "two-points-with-turn", "pts": [_p(0, 0), _p(100, 50)], "turn": 60},
    {"id": "two-points-no-turn-given", "pts": [_p(0, 0), _p(100, 50)]},
    {"id": "three-points-last-segment-with-last-turn", "pts": [_p(0, 0), _p(50, 0), _p(100, 40)], "last_turn": 70},
    {"id": "three-points-first-segment-unaffected-by-last-turn", "pts": [_p(0, 0), _p(50, 20), _p(100, 20)], "last_turn": 70},
    {"id": "four-points-mixed", "pts": [_p(0, 0), _p(40, 0), _p(40, 30), _p(80, 50)], "last_turn": 65},
    {"id": "already-elbowed-simplifies", "pts": [_p(0, 0), _p(50, 0), _p(50, 50), _p(50, 50), _p(100, 50)]},
]


@pytest.mark.parametrize("case", ELBOWS_CASES, ids=lambda c: c["id"])
def test_elbows_matches_node(node_golden, case):
    turn = case.get("turn")
    last_turn = case.get("last_turn")
    req = {"kind": "elbows", "pts": case["pts"]}
    if turn is not None:
        req["turn"] = turn
    if last_turn is not None:
        req["lastTurn"] = last_turn
    node_result = node_golden.call(req)
    assert elbows(case["pts"], turn, last_turn) == node_result


def _n(*ids: str, w: float = 40, h: float = 20) -> list[dict]:
    return [{"id": i, "size": {"w": w, "h": h}} for i in ids]


def _e(*pairs: tuple[str, str]) -> list[dict]:
    return [{"from": a, "to": b} for a, b in pairs]


CORRIDOR_CASES = [
    {"id": "single-direct-edge", "nodes": _n("a", "b"), "edges": _e(("a", "b")), "opts": {}},
    {"id": "three-direct-one-gap", "nodes": _n("a", "b", "c", "d"), "edges": _e(("a", "c"), ("b", "c"), ("b", "d")), "opts": {}},
    {"id": "with-outer-return", "nodes": _n("a", "b", "c"), "edges": _e(("a", "b"), ("b", "c"), ("c", "a")), "opts": {"back": [2], "outer": {"which": "all", "gap": 10, "step": 6}}},
]


@pytest.mark.parametrize("case", CORRIDOR_CASES, ids=lambda c: c["id"])
def test_corridor_load_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "corridorLoad", "nodes": case["nodes"], "edges": case["edges"], "opts": case["opts"]})
    lay = layout_layered(case["nodes"], case["edges"], case["opts"])
    assert corridor_load(lay) == node_result


LAYOUT_WITH_LANES_CASES = [
    {"id": "no-sharing-needed", "nodes": _n("a", "b"), "edges": _e(("a", "b")), "opts": {}, "chip": 0, "space": 1},
    {"id": "crowded-gap-widens-levelgap", "nodes": _n("a", "b", "c", "d", "e"), "edges": _e(("a", "d"), ("b", "d"), ("c", "e")), "opts": {"levelGap": 10}, "chip": 0, "space": 1},
    {"id": "with-chip-and-space", "nodes": _n("a", "b", "c", "d", "e"), "edges": _e(("a", "d"), ("b", "d"), ("c", "e")), "opts": {"levelGap": 10}, "chip": 30, "space": 0.75},
]


@pytest.mark.parametrize("case", LAYOUT_WITH_LANES_CASES, ids=lambda c: c["id"])
def test_layout_with_lanes_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutWithLanes", "nodes": case["nodes"], "edges": case["edges"], "opts": case["opts"], "chip": case["chip"], "space": case["space"]})
    py_result = layout_with_lanes(case["nodes"], case["edges"], case["opts"], case["chip"], case["space"])
    assert py_result == node_result
