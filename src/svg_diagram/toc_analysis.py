"""1:1 port of lib/toc-analysis.ts: counting over a cause tree's nodes and links (pure: no
layout, no fonts). The core driver of a current reality tree is the root cause that, through
the arrows, brings about the most undesirable effects (ADR 0015 D4).

Golden master: lib/toc-analysis.ts (Node.js, svg-diagram).
"""

from __future__ import annotations


def _walks(l: dict) -> bool:
    return not l.get("back") and l.get("kind") != "blocks"


def reach_counts(nodes: list[dict], links: list[dict]) -> dict[str, int]:
    """lib/toc-analysis.ts:14-34 reachCounts(): for every starting node (no arrow enters it),
    how many `ude` nodes its arrows reach, directly or through other nodes (itself not
    counted). An AND counts as arrows from each of its causes: every member reaches the
    effect. A cycle is walked once. `back` and `kind: 'blocks'` links cause nothing, so they
    are not walked."""
    next_: dict[str, list[str]] = {}
    entered: set[str] = set()
    for l in links:
        if not _walks(l):
            continue
        entered.add(l["to"])
        froms = [l["from"]] if isinstance(l["from"], str) else list(l["from"])
        for f in froms:
            next_.setdefault(f, []).append(l["to"])
    ude = {n["id"] for n in nodes if n.get("role") == "ude"}
    out: dict[str, int] = {}
    for n in nodes:
        if n["id"] in entered:
            continue
        seen = {n["id"]}
        stack = [n["id"]]
        count = 0
        while stack:
            cur = stack.pop()
            for t in next_.get(cur, []):
                if t not in seen:
                    seen.add(t)
                    stack.append(t)
                    if t in ude:
                        count += 1
        out[n["id"]] = count
    return out


def core_drivers(counts: dict[str, int]) -> list[str]:
    """lib/toc-analysis.ts:37-40 coreDrivers(): the starting nodes with the most reach, when
    that is 2 or more (a tie: all of them)."""
    top = max([0, *counts.values()])
    if top < 2:
        return []
    return [node_id for node_id, c in counts.items() if c == top]
