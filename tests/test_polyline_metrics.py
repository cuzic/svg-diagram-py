"""Golden-master tests for polyline_metrics.py against Node's lib/polyline-metrics.ts (all
exported — live-tested via emit_cli.ts). Pure point-geometry, shared by the (not yet ported)
layered-route.ts router and by the check/lint tool's edge-bends/edge-crossings rules (out of
this port's scope)."""

from __future__ import annotations

import pytest

from svg_diagram.polyline_metrics import (
    bends_of,
    crossings_of,
    crossings_with,
    runs_together,
    score_of,
    simplify,
    total_length,
)


def _p(x: float, y: float) -> dict:
    return {"x": x, "y": y}


STRAIGHT = [_p(0, 0), _p(50, 0), _p(100, 0)]
L_SHAPE = [_p(0, 0), _p(50, 0), _p(50, 50)]
Z_SHAPE = [_p(0, 0), _p(40, 0), _p(40, 30), _p(80, 30), _p(80, 60)]
WITH_DUP = [_p(0, 0), _p(0, 0), _p(50, 0), _p(50, 0.005), _p(100, 0)]
SELF_CROSSING_ISH = [_p(0, 0), _p(100, 0), _p(100, 100), _p(0, 100), _p(0, 50)]

SIMPLIFY_CASES = [STRAIGHT, L_SHAPE, Z_SHAPE, WITH_DUP, SELF_CROSSING_ISH, [_p(5, 5)], [_p(1, 1), _p(1, 1)]]


@pytest.mark.parametrize("pts", SIMPLIFY_CASES, ids=lambda p: f"n{len(p)}")
def test_simplify_matches_node(node_golden, pts):
    assert simplify(pts) == node_golden.call({"kind": "polySimplify", "pts": pts})


@pytest.mark.parametrize("pts", SIMPLIFY_CASES, ids=lambda p: f"n{len(p)}")
def test_bends_of_matches_node(node_golden, pts):
    assert bends_of(pts) == node_golden.call({"kind": "bendsOf", "points": pts})


@pytest.mark.parametrize("pts", SIMPLIFY_CASES, ids=lambda p: f"n{len(p)}")
def test_total_length_matches_node(node_golden, pts):
    node_result = node_golden.call({"kind": "totalLength", "points": pts})
    assert total_length(pts) == pytest.approx(node_result)


PATH_A = [_p(0, 0), _p(0, 50), _p(50, 50)]  # vertical then horizontal
PATH_B = [_p(25, 0), _p(25, 100)]  # a vertical line crossing A's horizontal run
PATH_C = [_p(-10, 50), _p(60, 50)]  # horizontal, overlapping A's horizontal run (no right-angle cross with it, but crosses B)
PATH_SELF = [_p(0, 0), _p(0, 50), _p(50, 50), _p(50, 0), _p(0, 0)]  # closed loop (self-crossing endpoints touch, not a true cross)

CROSSINGS_CASES = [
    {"id": "no-crossing", "paths": [STRAIGHT, [_p(0, 10), _p(100, 10)]]},
    {"id": "one-crossing", "paths": [PATH_A, PATH_B]},
    {"id": "three-paths", "paths": [PATH_A, PATH_B, PATH_C]},
    {"id": "closed-loop-alone", "paths": [PATH_SELF]},
    {"id": "margin-excludes-edge-touch", "paths": [PATH_A, PATH_B], "margin": 30},
    {"id": "tol-treats-near-level-as-level", "paths": [[_p(0, 0), _p(50, 0.4)], [_p(25, -10), _p(25, 10)]], "tol": 1},
]


@pytest.mark.parametrize("case", CROSSINGS_CASES, ids=lambda c: c["id"])
def test_crossings_of_matches_node(node_golden, case):
    kwargs = {k: case[k] for k in ("margin", "tol") if k in case}
    node_result = node_golden.call({"kind": "crossingsOf", "paths": case["paths"], **kwargs})
    assert crossings_of(case["paths"], **kwargs) == node_result


@pytest.mark.parametrize("case", CROSSINGS_CASES, ids=lambda c: c["id"])
def test_crossings_with_matches_node(node_golden, case):
    path, others = case["paths"][0], case["paths"][1:]
    kwargs = {k: case[k] for k in ("margin", "tol") if k in case}
    node_result = node_golden.call({"kind": "crossingsWith", "path": path, "others": others, **kwargs})
    assert crossings_with(path, others, **kwargs) == node_result


SCORE_CASES = [[STRAIGHT], [PATH_A, PATH_B], [PATH_A, PATH_B, PATH_C, Z_SHAPE]]


@pytest.mark.parametrize("paths", SCORE_CASES, ids=lambda p: f"n{len(p)}")
def test_score_of_matches_node(node_golden, paths):
    assert score_of(paths) == node_golden.call({"kind": "scoreOf", "paths": paths})


RUNS_TOGETHER_CASES = [
    {"id": "parallel-close-horizontal", "a": {"p": _p(0, 10), "q": _p(50, 10)}, "b": {"p": _p(0, 12), "q": _p(50, 12)}},
    {"id": "parallel-far-apart", "a": {"p": _p(0, 10), "q": _p(50, 10)}, "b": {"p": _p(0, 50), "q": _p(50, 50)}},
    {"id": "different-orientation", "a": {"p": _p(0, 10), "q": _p(50, 10)}, "b": {"p": _p(10, 0), "q": _p(10, 50)}},
    {"id": "close-but-short-overlap", "a": {"p": _p(0, 10), "q": _p(2, 10)}, "b": {"p": _p(0, 11), "q": _p(2, 11)}},
    {"id": "parallel-close-vertical", "a": {"p": _p(10, 0), "q": _p(10, 50)}, "b": {"p": _p(12, 0), "q": _p(12, 50)}},
]


@pytest.mark.parametrize("case", RUNS_TOGETHER_CASES, ids=lambda c: c["id"])
def test_runs_together_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "runsTogether", "a": case["a"], "b": case["b"]})
    assert runs_together(case["a"], case["b"]) == node_result
