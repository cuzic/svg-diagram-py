"""1:1 port of lib/fta-analysis.ts: the minimal cut sets of a fault tree (ADR 0025 D4, U2,
built bottom-up) and the probability of its top event (ADR 0025 D4, U4). A pure function of
the resolved tree (fta.py's FtaNode dicts); no layout, no fonts.

Golden master: lib/fta-analysis.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

CUT_SET_LIMIT = 5000
SHARED_LIMIT = 12


def fta_var(n: dict) -> str:
    """lib/fta-analysis.ts:17 ftaVar()."""
    if n.get("copyOf") is not None:
        return f"id:{n['copyOf']}"
    if n.get("id") is not None:
        return f"id:{n['id']}"
    return f"k:{n['key']}"


class _TooMany(Exception):
    pass


def _union(a: list[str], b: list[str]) -> list[str]:
    return sorted(set(a) | set(b))


def _subset(a: list[str], b: list[str]) -> bool:
    return len(a) <= len(b) and all(v in b for v in a)


def _absorb(sets: list[list[str]]) -> list[list[str]]:
    """lib/fta-analysis.ts:25-30 absorb(): keeps the sets no other set is contained in."""
    dedup: dict[str, list[str]] = {}
    for s in sets:
        dedup["\0".join(s)] = s
    ordered = sorted(dedup.values(), key=len)
    out: list[list[str]] = []
    for s in ordered:
        if not any(_subset(o, s) for o in out):
            out.append(s)
    return out


def _guard(n: int) -> None:
    if n > CUT_SET_LIMIT:
        raise _TooMany


def _and(parts: list[list[list[str]]]) -> list[list[str]]:
    acc: list[list[str]] = [[]]
    for p in parts:
        _guard(len(acc) * len(p))
        acc = _absorb([_union(a, b) for a in acc for b in p])
    return acc


def _choose(items: list, k: int) -> list[list]:
    out: list[list] = []

    def go(frm: int, picked: list) -> None:
        if len(picked) == k:
            out.append(picked)
            return
        for i in range(frm, len(items)):
            go(i + 1, [*picked, items[i]])
            _guard(len(out))

    go(0, [])
    return out


def _sets_of(n: dict) -> list[list[str]]:
    """lib/fta-analysis.ts:54-68 setsOf(): [] = never happens, [[]] = always happens."""
    if n.get("gate") is None:
        if n["kind"] == "house":
            return [[]] if n.get("state") else []
        return [[fta_var(n)]]
    kids = [_sets_of(c) for c in n["children"]]
    if n["gate"] == "or":
        _guard(sum(len(k) for k in kids))
        return _absorb([s for k in kids for s in k])
    if n["gate"] == "and":
        return _and(kids)
    if n["gate"] == "inhibit":
        return _and([*kids, _sets_of(n["cond"])])
    combos = _choose(kids, n["k"])
    _guard(len(combos))
    all_: list[list[str]] = []
    for c in combos:
        all_.extend(_and(c))
        _guard(len(all_))
    return _absorb(all_)


def minimal_cut_sets(root: dict) -> dict:
    """lib/fta-analysis.ts:71-81 minimalCutSets()."""
    try:
        raw = _sets_of(root)
        _guard(len(raw))
        sets = sorted(_absorb(raw), key=lambda s: (len(s), ",".join(s)))
        return {"sets": sets, "truncated": False}
    except _TooMany:
        return {"sets": [], "truncated": True}


def single_points(cuts: dict) -> set[str]:
    """lib/fta-analysis.ts:84-86 singlePoints(): the cut sets of size 1."""
    return {s[0] for s in cuts["sets"] if len(s) == 1}


def _leaf_p(n: dict) -> float:
    if n["kind"] == "house":
        return 1.0 if n.get("state") else 0.0
    p = n.get("p")
    return float(p) if p is not None else math.nan


def _at_least(ps: list[float], k: int) -> float:
    """lib/fta-analysis.ts:103-111 atLeast(): P(at least k of the inputs happen)."""
    dp = [1.0]
    for p in ps:
        nxt = [0.0] * (len(dp) + 1)
        for j, q in enumerate(dp):
            nxt[j] += q * (1 - p)
            nxt[j + 1] += q * p
        dp = nxt
    return sum(dp[k:])


def top_probability(root: dict) -> dict:
    """lib/fta-analysis.ts:114-149 topProbability()."""
    count: dict[str, int] = {}
    p_of: dict[str, float] = {}

    def scan(n: dict) -> None:
        if n.get("gate") is None:
            v = fta_var(n)
            count[v] = count.get(v, 0) + 1
            p_of[v] = _leaf_p(n)
        for c in n.get("children") or []:
            scan(c)
        if n.get("cond"):
            scan(n["cond"])

    scan(root)
    shared = [v for v, c in count.items() if c > 1 and 0 < p_of.get(v, math.nan) < 1]
    if len(shared) > SHARED_LIMIT:
        cuts = minimal_cut_sets(root)
        if cuts["truncated"]:
            raise ValueError("faultTree({quant: true}): the tree has too many cut sets to bound the probability; simplify the tree")
        acc = 1.0
        for s in cuts["sets"]:
            acc *= 1 - math.prod(p_of[v] for v in s)
        return {"p": 1 - acc, "bound": True}

    def eval_at(n: dict, fixed: dict[str, int]) -> float:
        if n.get("gate") is None:
            v = fta_var(n)
            return fixed[v] if v in fixed else _leaf_p(n)
        kids = [eval_at(c, fixed) for c in n["children"]]
        if n["gate"] == "and":
            acc = 1.0
            for k in kids:
                acc *= k
            return acc
        if n["gate"] == "or":
            acc = 1.0
            for k in kids:
                acc *= 1 - k
            return 1 - acc
        if n["gate"] == "inhibit":
            return kids[0] * eval_at(n["cond"], fixed)
        return _at_least(kids, n["k"])

    total = 0.0
    for mask in range(1 << len(shared)):
        fixed: dict[str, int] = {}
        weight = 1.0
        for i, v in enumerate(shared):
            on = (mask >> i) & 1
            p = p_of[v]
            fixed[v] = on
            weight *= p if on else (1 - p)
        total += weight * eval_at(root, fixed)
    return {"p": total, "bound": False}
