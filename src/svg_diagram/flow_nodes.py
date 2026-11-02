"""1:1 port of lib/flow-nodes.ts: the shapes a flowchart adds to a state diagram (ADR 0041):
a decision is a diamond that holds its text, a terminator is a pill. Pure: sizes come from
the measured text, and an arrow that ends on a diamond is brought to its outline.

Golden master: lib/flow-nodes.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import text_width
from .emit_common import js_round
from .tree_text import measure_node

_PAD_X = 14  # tree.ts's box padding: a pill keeps its text this far from the straight part
_DIAMOND_RATIO, _TEXT_PAD_X, _TEXT_PAD_Y, _MIN_TEXT_W = 1.6, 8, 6, 88


def _grid8(v: float) -> float:
    return math.ceil(v / 8) * 8


def _line_h(s: float) -> float:
    return js_round(s * 1.4)


def diamond_lines(label: str, sub: str | None, max_w: float, icon_h: float, width_of, roles: dict, mode: str, floor: bool) -> dict:
    """lib/flow-nodes.ts:16-33 diamondLines(): the diamond that holds a text, as small as it
    can be. Several widths of text are tried and the narrowest diamond wins."""
    L, S = roles["body"], roles["note"]

    def measure(mw: float) -> dict:
        return measure_node(label, sub, mw, width_of, roles, mode, floor, keep_words=True)

    # the widths to try for a line of text: a fixed grid up to the cap, so a larger cap only adds choices and can never give a wider diamond
    widths: list[float] = []
    mw = _MIN_TEXT_W
    cap = math.floor(max_w / 8) * 8
    while mw <= cap:
        widths.append(mw)
        mw += 8
    if not widths:
        widths.append(max_w)
    best: dict | None = None
    for mw in widths:
        m = measure(mw)
        tw = max([text_width(width_of, l, L, 700) for l in m["label"]] + [text_width(width_of, l, S, 400) for l in m["sub"]])
        th = len(m["label"]) * _line_h(L) + len(m["sub"]) * _line_h(S) + icon_h
        w = _grid8((tw + 2 * _TEXT_PAD_X) + _DIAMOND_RATIO * (th + 2 * _TEXT_PAD_Y))
        h = _grid8(w / _DIAMOND_RATIO)
        if best is None or w < best["w"] or (w == best["w"] and h < best["h"]):
            best = {"label": m["label"], "sub": m["sub"], "w": w, "h": h}
    assert best is not None
    return best


def pill_lines(l: dict, icon_h: float) -> dict:
    """lib/flow-nodes.ts:36-39 pillLines(): a terminator — the box of the text, with room at
    both ends for the rounding (the radius is half the height)."""
    h = l["h"] + icon_h
    return {**l, "h": h, "w": l["w"] + 2 * max(0, math.ceil(h / 2) - _PAD_X)}


def diamond_points(r: dict) -> list[dict]:
    """lib/flow-nodes.ts:42 diamondPoints(): the four vertices of a diamond (top, right,
    bottom, left) inside rect r."""
    return [
        {"x": r["x"] + r["w"] / 2, "y": r["y"]},
        {"x": r["x"] + r["w"], "y": r["y"] + r["h"] / 2},
        {"x": r["x"] + r["w"] / 2, "y": r["y"] + r["h"]},
        {"x": r["x"], "y": r["y"] + r["h"] / 2},
    ]


def _half_extent(off: float, half: float, along: float) -> float:
    return along * (1 - min(1, abs(off) / half))


def onto_diamond(end: dict, next_: dict, r: dict) -> dict:
    """lib/flow-nodes.ts:51-61 ontoDiamond(): an arrow that starts or ends on a diamond is
    routed to the rect's side; this moves that end along the arrow's last (first) segment
    onto the outline. `end` is the point at the node's side, `next_` its neighbour on the
    arrow. Other points are left as they are."""
    cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
    if end["x"] == next_["x"] and end["y"] != next_["y"]:  # a vertical segment meets the top or the bottom
        top = end["y"] <= cy
        d = _half_extent(end["x"] - cx, r["w"] / 2, r["h"] / 2)
        return {"x": end["x"], "y": (r["y"] + (r["h"] / 2 - d)) if top else (r["y"] + r["h"] - (r["h"] / 2 - d))}
    if end["y"] == next_["y"] and end["x"] != next_["x"]:  # a horizontal one meets the left or the right
        left = end["x"] <= cx
        d = _half_extent(end["y"] - cy, r["h"] / 2, r["w"] / 2)
        return {"x": (r["x"] + (r["w"] / 2 - d)) if left else (r["x"] + r["w"] - (r["w"] / 2 - d)), "y": end["y"]}
    return end


def _overlaps(a: dict, b: dict) -> bool:
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def vertex_drops(outs: list[dict], r: dict, others: list[dict]) -> list[list[dict]]:
    """lib/flow-nodes.ts:70-85 vertexDrops(): the arrows that leave a diamond straight down
    start at the diamond's corners instead of at spots on its lower sides. `outs`:
    [{"pts", "target"}, ...], in the order to return. `others` is checked by object identity
    (`is not`, matching Node's `!==`) against each `out`'s `target` — the caller must pass the
    SAME dict object for a target that also appears in `others` (see states.py's `sw_r`,
    which is the identity function when not flipped, exactly mirroring Node's `swR`)."""

    def straight(o: dict) -> bool:
        pts = o["pts"]
        return len(pts) == 2 and pts[0]["x"] == pts[1]["x"] and pts[1]["y"] > pts[0]["y"]

    cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
    result = [o["pts"] for o in outs]
    movable = [{"o": o, "i": i} for i, o in enumerate(outs) if straight(o)]
    if len(movable) < 1 or len(movable) > 3 or len(movable) < len(outs):  # a mix of shapes: leave the diamond as it is
        return result
    corners = [r["x"], cx, r["x"] + r["w"]] if len(movable) == 3 else [r["x"], r["x"] + r["w"]] if len(movable) == 2 else [cx]
    movable.sort(key=lambda m: m["o"]["target"]["x"] + m["o"]["target"]["w"] / 2)
    next_: list[list[dict]] = list(result)  # all or nothing: the answers must line up, so a failure keeps every path
    for k, m in enumerate(movable):
        o, i = m["o"], m["i"]
        x, t, tip = corners[k], o["target"], o["pts"][1]
        if x < t["x"] + 10 or x > t["x"] + t["w"] - 10:  # the target is not under this corner: keep every path (the answers would not line up)
            return result
        seg = {"x": x - 1, "y": cy, "w": 2, "h": tip["y"] - cy}
        if any(b is not t and _overlaps(seg, b) for b in others):
            return result
        next_[i] = [{"x": x, "y": cy}, {"x": x, "y": tip["y"]}]
    return next_
