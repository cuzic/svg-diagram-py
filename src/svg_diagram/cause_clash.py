"""1:1 port of lib/cause-clash.ts: two arrows into one effect that has an AND must not cross,
and must not run side by side (which arrow belongs to the AND would be unclear). One
definition, used by the verifier (not in this port's scope) and by causeTree()'s order
search (ADR 0019 D4).

Golden master: lib/cause-clash.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .polyline_metrics import runs_together


def _cross(a: dict, b: dict) -> bool:
    a_h = a["p"]["y"] == a["q"]["y"]
    b_h = b["p"]["y"] == b["q"]["y"]
    if a_h == b_h:
        return False
    h, v = (a, b) if a_h else (b, a)
    return (
        v["p"]["x"] > min(h["p"]["x"], h["q"]["x"]) + 0.5
        and v["p"]["x"] < max(h["p"]["x"], h["q"]["x"]) - 0.5
        and h["p"]["y"] > min(v["p"]["y"], v["q"]["y"]) + 0.5
        and h["p"]["y"] < max(v["p"]["y"], v["q"]["y"]) - 0.5
    )


def and_clashes(edges: list[dict], ands: list[dict]) -> list[dict]:
    """lib/cause-clash.ts:14-28 andClashes(): the pairs of arrows into an effect with an AND
    that cross or run together (each pair once, in the order found). A crossing elsewhere is
    left alone. `edges`: [{from, to, points}]. `ands`: [{to}]."""
    and_to = {x["to"] for x in ands}
    segs: list[dict] = []
    for k, e in enumerate(edges):
        if e["to"] not in and_to:
            continue
        pts = e["points"]
        for m in range(len(pts) - 1):
            segs.append({"k": k, "p": pts[m], "q": pts[m + 1]})
    out: list[dict] = []
    flagged: set[str] = set()
    for i, si in enumerate(segs):
        for sj in segs[i + 1 :]:
            a, b = edges[si["k"]], edges[sj["k"]]
            if si["k"] == sj["k"] or a["to"] != b["to"]:
                continue
            how = "crosses" if _cross(si, sj) else "runs together with" if runs_together(si, sj) else None
            key = f"{min(si['k'], sj['k'])}:{max(si['k'], sj['k'])}"
            if how is None or key in flagged:
                continue
            flagged.add(key)
            out.append({"a": a, "b": b, "how": how})
    return out
