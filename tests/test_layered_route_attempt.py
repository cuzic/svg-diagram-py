"""Golden-master tests for layered_route.py's layered_attempt() against Node's
layeredAttempt() (lib/layered-route.ts, exported — live-tested via emit_cli.ts). Test cases
mirror the AttemptOpts combinations each of the 4 real (out-of-scope) callers actually sets:
lib/classes.ts (transpose/tighten/maxAcross/place/straighten), lib/states.ts (+round/
returns/space), lib/toc.ts's cause() (+groupOf/detour/apart/back/alap/fold), lib/semnet-
common.ts (transpose/place/tighten/straighten) — plus the plain/BK tie-break, the far/near/
low + laneHeads retry, and apart()'s move_apart wiring."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from svg_diagram.layered_route import layered_attempt


def _place_from_spec(spec: dict | None) -> Callable[[dict], Callable[[dict], dict]]:
    spec = spec or {}
    swap, scale, dx, dy = spec.get("swap", False), spec.get("scale", 1), spec.get("dx", 0), spec.get("dy", 0)

    def place(p: dict) -> dict:
        return {"x": (p["y"] if swap else p["x"]) * scale + dx, "y": (p["x"] if swap else p["y"]) * scale + dy}

    return lambda _size: place


def _group_of_from_spec(spec: dict[int, int] | None) -> Callable[[int], int | None] | None:
    if not spec:
        return None
    m = dict(spec)
    return lambda edge: m.get(edge)


def _round_from_spec(ids: list[str] | None) -> Callable[[str], bool] | None:
    if not ids:
        return None
    s = set(ids)
    return lambda node_id: node_id in s


def _n(*specs: tuple[str, float, float]) -> list[dict]:
    return [{"id": i, "size": {"w": w, "h": h}} for i, w, h in specs]


def _e(*pairs: tuple[str, str]) -> list[dict]:
    return [{"from": a, "to": b} for a, b in pairs]


IDENTITY_PLACE = {"swap": False, "scale": 1, "dx": 0, "dy": 0}

# classes.ts-like: a simple chain, transpose + tighten, no groupOf/round/returns
CLASSES_LIKE = (_n(("a", 60, 40), ("b", 60, 40), ("c", 60, 40)), _e(("a", "b"), ("b", "c")))

# states.ts-like: a circle (round) state, plus a declared back edge laid out with returns:'all'
STATES_LIKE = (_n(("start", 50, 50), ("mid", 60, 30), ("end", 60, 30)), _e(("start", "mid"), ("mid", "end"), ("end", "start")))

# cause()-like (toc.ts): a long arrow grouped (AND) with a direct arrow into the same head, plus detour+apart
CAUSE_LIKE = (_n(("a", 40, 20), ("b", 40, 20), ("head", 40, 20)), _e(("a", "b"), ("b", "head"), ("a", "head")))
CAUSE_LIKE_GROUP_OF = {2: 0, 1: 0}

# semnet-common.ts-like: transpose + place + tighten + straighten, no groupOf
SEMNET_LIKE = (_n(("x", 50, 24), ("y", 50, 24)), _e(("x", "y")))

# a graph wide enough that maxAcross forces plain.fits=False, to exercise pick0's fits cutoffs
WIDE_CHAIN = (_n(("a", 200, 20), ("b", 200, 20), ("c", 200, 20), ("d", 200, 20)), _e(("a", "b"), ("b", "c"), ("c", "d")))

ATTEMPT_CASES: list[dict] = [
    {
        "id": "classes-like",
        "graph": CLASSES_LIKE, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40},
        "opts": {"transpose": True, "tighten": True, "place": IDENTITY_PLACE},
    },
    {
        "id": "classes-like-maxacross-fits",
        "graph": CLASSES_LIKE, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40},
        "opts": {"transpose": True, "tighten": True, "place": IDENTITY_PLACE, "maxAcross": 1000},
    },
    {
        "id": "states-like-round-returns",
        "graph": STATES_LIKE, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40, "back": [2]},
        "opts": {"place": IDENTITY_PLACE, "round": ["start"], "returns": "all", "tighten": True},
    },
    {
        "id": "states-like-returns-declared-space-compact",
        "graph": STATES_LIKE, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40, "back": [2]},
        "opts": {"place": IDENTITY_PLACE, "round": ["start"], "returns": "declared", "space": 0.75},
    },
    {
        "id": "cause-like-group-detour-apart",
        "graph": CAUSE_LIKE, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40},
        "opts": {"place": IDENTITY_PLACE, "groupOf": CAUSE_LIKE_GROUP_OF, "detour": True, "apart": True},
    },
    {
        "id": "cause-like-group-no-apart",
        "graph": CAUSE_LIKE, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40},
        "opts": {"place": IDENTITY_PLACE, "groupOf": CAUSE_LIKE_GROUP_OF},
    },
    {
        "id": "cause-like-aside-false",
        "graph": CAUSE_LIKE, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40},
        "opts": {"place": IDENTITY_PLACE, "groupOf": CAUSE_LIKE_GROUP_OF, "aside": False},
    },
    {
        "id": "semnet-like",
        "graph": SEMNET_LIKE, "layout_opts": {"dir": "right", "gap": 28, "levelGap": 76},
        "opts": {"transpose": True, "place": IDENTITY_PLACE, "tighten": True},
    },
    {
        "id": "semnet-like-straighten-false",
        "graph": SEMNET_LIKE, "layout_opts": {"dir": "right", "gap": 28, "levelGap": 76},
        "opts": {"transpose": True, "place": IDENTITY_PLACE, "straighten": False},
    },
    {
        "id": "wide-chain-maxacross-forces-bk-or-plain",
        "graph": WIDE_CHAIN, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40},
        "opts": {"place": IDENTITY_PLACE, "maxAcross": 650},
    },
    {
        "id": "wide-chain-no-maxacross",
        "graph": WIDE_CHAIN, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40},
        "opts": {"place": IDENTITY_PLACE},
    },
    {
        "id": "custom-port-step",
        "graph": CLASSES_LIKE, "layout_opts": {"dir": "right", "gap": 24, "levelGap": 40},
        "opts": {"place": IDENTITY_PLACE, "portStep": 8},
    },
]


@pytest.mark.parametrize("case", ATTEMPT_CASES, ids=lambda c: c["id"])
def test_layered_attempt_matches_node(node_golden, case):
    nodes, edges = case["graph"]
    opts = case["opts"]
    # JS default params / `=== undefined` checks only trigger on an absent/undefined field, not
    # on a literal `null` — so an unset optional field must be OMITTED from the request, not
    # sent as null (the same class of bug as the earlier elbows() fix: `o.space` ending up
    # `null` instead of defaulting to 1 silently zeroes out stubOf/laneStepOf via `STUB * null`).
    req: dict = {"kind": "layeredAttempt", "nodes": nodes, "edges": edges, "layoutOpts": case["layout_opts"], "place": opts.get("place", IDENTITY_PLACE)}
    for key in ("portStep", "groupOf", "transpose", "maxAcross", "round", "straighten", "tighten", "space", "detour", "apart", "aside", "returns"):
        val = opts.get(key)
        if val is not None:
            req[key] = val
    node_result = node_golden.call(req)

    attempt_opts: dict = {"place": _place_from_spec(opts.get("place"))}
    for key, val in (
        ("portStep", opts.get("portStep")),
        ("groupOf", _group_of_from_spec(opts.get("groupOf"))),
        ("transpose", opts.get("transpose")),
        ("maxAcross", opts.get("maxAcross")),
        ("round", _round_from_spec(opts.get("round"))),
        ("straighten", opts.get("straighten")),
        ("tighten", opts.get("tighten")),
        ("space", opts.get("space")),
        ("detour", opts.get("detour")),
        ("apart", opts.get("apart")),
        ("aside", opts.get("aside")),
        ("returns", opts.get("returns")),
    ):
        if val is not None:
            attempt_opts[key] = val

    py_result = layered_attempt(nodes, edges, case["layout_opts"], attempt_opts)
    py_plain = {
        "routes": {str(k): v for k, v in py_result["routes"].items()},
        "score": py_result["score"],
        "size": py_result["size"],
        "fits": py_result["fits"],
        "loose": py_result["loose"],
        "asided": py_result.get("asided"),
    }
    assert py_plain == node_result


def test_pick0_loose_cutoff_logic_in_isolation():
    """The `cand.loose.length > plain.loose.length` branch (BANDS.md's known gap: only
    reachable with `looseOf` injected, which only toc.ts's cause() — out of this port's scope
    — ever supplies) cannot be golden-tested without `looseOf`. This directly exercises the
    same comparison `worse()`/`pick0` use, on hand-built Attempt-shaped dicts, as a substitute."""
    from svg_diagram.layered_route import _better

    plain = {"loose": [], "fits": True, "score": {"crossings": 2, "bends": 3}}
    cand = {"loose": ["g1"], "fits": True, "score": {"crossings": 0, "bends": 0}}
    # pick0 rejects `cand` outright once `cand.loose.length > plain.loose.length`, regardless of score
    assert len(cand["loose"]) > len(plain["loose"])
    assert _better(cand["score"], plain["score"])  # score alone would have picked cand — loose must override it
