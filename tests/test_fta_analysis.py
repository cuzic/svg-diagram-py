"""Unit tests for fta_analysis.py's minimal_cut_sets()/top_probability() — the vote/inhibit
gate paths, the house-event "never/always happens" branches, the shared-variable probability
paths (both the exact Shannon-expansion enumeration and the >SHARED_LIMIT min-cut bound), and
the CUT_SET_LIMIT truncation guard, none of which the existing layout-focused golden tests in
test_fta.py happen to exercise. Expected values are derived by hand from the documented
algorithm (ADR 0025 D4, U2/U4; see lib/fta-analysis.ts), not by re-running the port, so these
catch divergence from the intended semantics, not just regressions in the port itself.

Trees are built with fta_resolve() from the same DSL shape as test_fta.py, so fta_analysis's
inputs are real resolved FtaNode dicts, not hand-rolled ones that might not match reality.
"""

from __future__ import annotations

import pytest

from svg_diagram.fta import fta_resolve
from svg_diagram.fta_analysis import fta_var, minimal_cut_sets, single_points, top_probability


def _resolve(top: dict) -> dict:
    return fta_resolve(top)["root"]


def test_vote_gate_cut_sets_are_every_k_combination():
    root = _resolve({
        "label": "top", "gate": "vote", "k": 2,
        "children": [
            {"label": "A", "kind": "basic", "p": 0.1},
            {"label": "B", "kind": "basic", "p": 0.2},
            {"label": "C", "kind": "basic", "p": 0.3},
        ],
    })
    a, b, c = (fta_var(ch) for ch in root["children"])
    cuts = minimal_cut_sets(root)
    assert cuts["truncated"] is False
    assert {frozenset(s) for s in cuts["sets"]} == {frozenset([a, b]), frozenset([a, c]), frozenset([b, c])}
    assert single_points(cuts) == set()


def test_vote_gate_probability_matches_at_least_k_formula():
    root = _resolve({
        "label": "top", "gate": "vote", "k": 2,
        "children": [
            {"label": "A", "kind": "basic", "p": 0.1},
            {"label": "B", "kind": "basic", "p": 0.2},
            {"label": "C", "kind": "basic", "p": 0.3},
        ],
    })
    result = top_probability(root)
    assert result["bound"] is False
    # P(>=2 of 3 independent) = sum over pairs happening with the third not, plus all three.
    expected = 0.1 * 0.2 * 0.7 + 0.1 * 0.3 * 0.8 + 0.2 * 0.3 * 0.9 + 0.1 * 0.2 * 0.3
    assert result["p"] == pytest.approx(expected)


def test_house_event_false_makes_and_impossible():
    root = _resolve({
        "label": "top", "gate": "and",
        "children": [
            {"label": "never", "kind": "house", "state": False},
            {"label": "b", "kind": "basic", "p": 0.5},
        ],
    })
    cuts = minimal_cut_sets(root)
    assert cuts == {"sets": [], "truncated": False}
    assert single_points(cuts) == set()
    assert top_probability(root) == {"p": 0.0, "bound": False}


def test_house_event_true_is_an_identity_under_and():
    root = _resolve({
        "label": "top", "gate": "and",
        "children": [
            {"label": "always", "kind": "house", "state": True},
            {"label": "b", "kind": "basic", "p": 0.5},
        ],
    })
    b = fta_var(root["children"][1])
    cuts = minimal_cut_sets(root)
    assert cuts["sets"] == [[b]]
    assert single_points(cuts) == {b}
    result = top_probability(root)
    assert result["bound"] is False
    assert result["p"] == pytest.approx(0.5)


def test_inhibit_gate_cut_set_and_probability_combine_child_and_condition():
    root = _resolve({
        "label": "top", "gate": "inhibit",
        "children": [{"label": "c", "kind": "basic", "p": 0.03}],
        "condition": {"label": "cond", "p": 0.2},
    })
    child_var, cond_var = fta_var(root["children"][0]), fta_var(root["cond"])
    cuts = minimal_cut_sets(root)
    assert {frozenset(s) for s in cuts["sets"]} == {frozenset([child_var, cond_var])}
    result = top_probability(root)
    assert result["bound"] is False
    assert result["p"] == pytest.approx(0.03 * 0.2)


def test_shared_variable_uses_exact_shannon_expansion():
    # "shared" repeats (via {ref: "shared"}) under both sides of the OR, so it isn't independent
    # of itself — only the exact mask-enumeration path (not a plain OR-of-ANDs formula) is right.
    root = _resolve({
        "label": "top", "gate": "or",
        "children": [
            {"label": "A", "gate": "and", "children": [
                {"label": "shared", "kind": "basic", "id": "shared", "p": 0.2},
                {"label": "u1", "kind": "basic", "p": 0.1},
            ]},
            {"label": "B", "gate": "and", "children": [
                {"ref": "shared"},
                {"label": "u2", "kind": "basic", "p": 0.3},
            ]},
        ],
    })
    result = top_probability(root)
    assert result["bound"] is False
    # P(shared) * P(u1 or u2); P(top | not shared) = 0 since both branches need `shared`.
    expected = 0.2 * (1 - (1 - 0.1) * (1 - 0.3))
    assert result["p"] == pytest.approx(expected)


def _shared_basics(prefix: str, n: int, p: float = 0.1) -> list[dict]:
    return [{"label": f"{prefix}{i}", "kind": "basic", "id": f"{prefix}{i}", "p": p} for i in range(n)]


def _shared_refs(prefix: str, n: int) -> list[dict]:
    return [{"ref": f"{prefix}{i}"} for i in range(n)]


def _exploding_and(prefix: str, groups: int = 7, width: int = 4) -> dict:
    """An AND of `groups` OR-gates of `width` distinct basics each: cross-multiplies the cut
    set count group by group (4, 16, 64, ... ) and passes CUT_SET_LIMIT partway through, with
    `groups=7, width=4` chosen so the 7th multiplication (4096 * 4 = 16384) is the one that
    trips the guard."""
    return {
        "label": f"{prefix}-boom", "gate": "and",
        "children": [
            {"label": f"{prefix}-or{g}", "gate": "or", "children": [{"label": f"{prefix}-{g}-{i}", "kind": "basic", "p": 0.1} for i in range(width)]}
            for g in range(groups)
        ],
    }


def test_minimal_cut_sets_truncates_past_the_limit():
    root = _resolve(_exploding_and("x"))
    assert minimal_cut_sets(root) == {"sets": [], "truncated": True}


def test_top_probability_bounds_when_shared_variables_exceed_the_limit():
    # 13 variables repeated (original + ref) each, so shared.length (13) > SHARED_LIMIT (12):
    # falls back to the min-cut upper bound instead of enumerating 2**13 masks.
    root = _resolve({
        "label": "top", "gate": "or",
        "children": [
            {"label": "A", "gate": "and", "children": _shared_basics("x", 13)},
            {"label": "B", "gate": "and", "children": _shared_refs("x", 13)},
        ],
    })
    result = top_probability(root)
    assert result["bound"] is True
    # A and B are literally the same 13-variable AND repeated, so the one minimal cut set is
    # "all 13 fail" and the bound is exact here: P = 0.1**13.
    assert result["p"] == pytest.approx(0.1**13)


def test_top_probability_raises_when_the_bound_itself_would_need_truncated_cut_sets():
    root = _resolve({
        "label": "top", "gate": "or",
        "children": [
            {"label": "A", "gate": "and", "children": _shared_basics("x", 13)},
            {"label": "B", "gate": "and", "children": _shared_refs("x", 13)},
            _exploding_and("y"),
        ],
    })
    with pytest.raises(ValueError, match="too many cut sets"):
        top_probability(root)
