"""1:1 port of the small, generic pieces of lib/charts-base.ts that bars.py needs. The
`Canvas` class and the rest of charts-base.ts (used by waterfall/heatmap/radar/... — not yet
ported) are left for when those chart types are ported.

Golden master: lib/charts-base.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .emit_common import js_round


def overlaps(a: dict, b: dict) -> bool:
    """lib/charts-base.ts:55 overlaps()."""
    return min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]) > 0.5 and min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]) > 0.5


def fail(who: str, msg: str):
    """lib/charts-base.ts:196 fail()."""
    raise ValueError(f"{who}(): {msg}")


def inset_or_need(who: str, inset: tuple[float, float] | None, need_left: float, need_right: float) -> tuple[float, float]:
    """lib/charts-base.ts:92-96 insetOrNeed()."""
    import math

    if inset is None:
        return (need_left, need_right)
    if inset[0] < need_left - 0.5 or inset[1] < need_right - 0.5:
        fail(
            who,
            f"plotInset [{js_round(inset[0])}, {js_round(inset[1])}] leaves too little room for the labels: "
            f"this chart needs at least [{math.ceil(need_left)}, {math.ceil(need_right)}] (write the largest of the charts you want to line up)",
        )
    return (inset[0], inset[1])
