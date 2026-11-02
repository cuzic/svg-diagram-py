"""1:1 port of lib/emblem-shapes.ts (ADR 0043, 0044): the outlines of emblem() shapes.

For each shape, a width D (a multiple of 8) and a top-left give the drawn outline, the
rectangle where text fits, and the rectangle connect() ties to. Pure geometry;
flow_shapes.py lays the labels out in it.

NOT ported: emblemClearance()/flatOutline() (tuning/test-only helpers for EMBLEM_TEXT,
not used by layoutEmblem or renderFlowShape, and not exposed by the golden CLI).

Golden master: lib/emblem-shapes.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .emit_common import js_num, js_round

EmblemShape = str  # 'circle' | 'square' | 'triangle' | 'diamond' | 'hexagon' | 'trapezoid'
# | 'inverted-trapezoid' | 'parallelogram' | 'pentagon-down' | 'pill' | 'rounded'
# | 'document' | 'cylinder'

EMBLEM_SHAPES: list[str] = [
    "circle", "square", "triangle", "diamond", "hexagon", "trapezoid",
    "inverted-trapezoid", "parallelogram", "pentagon-down", "pill", "rounded",
    "document", "cylinder",
]

EMBLEM_TEXT: dict[str, dict[str, float]] = {
    "circle": {"w": 0.76, "h": 0.56}, "square": {"w": 0.84, "h": 0.84}, "diamond": {"w": 0.56, "h": 0.34},
    "hexagon": {"w": 0.68, "h": 0.5}, "triangle": {"w": 0.54, "h": 0.32},
    "trapezoid": {"w": 0.6, "h": 0.3}, "inverted-trapezoid": {"w": 0.6, "h": 0.3}, "parallelogram": {"w": 0.56, "h": 0.28},
    "pentagon-down": {"w": 0.76, "h": 0.32}, "pill": {"w": 0.72, "h": 0.3}, "rounded": {"w": 0.84, "h": 0.46},
    "document": {"w": 0.84, "h": 0.42}, "cylinder": {"w": 0.84, "h": 0.4},
}

EMBLEM_FLEX: set[str] = {"pill", "rounded", "parallelogram", "document", "cylinder"}

_MAX_HEIGHT: dict[str, float] = {"pill": 0.75, "parallelogram": 1.2}


def _g4(v: float) -> float:
    return js_round(v / 4) * 4


def _up4(v: float) -> float:
    return math.ceil(v / 4) * 4


def emblem_height(shape: str, d: float, text_h: float = 0) -> float:
    """lib/emblem-shapes.ts:34-43 emblemHeight()."""
    if shape == "pill":
        return max(d / 2, _up4(text_h / 0.6))
    if shape == "rounded":
        return max(_g4(0.7 * d), _up4(text_h + 0.24 * d))
    if shape == "parallelogram":
        return max(_g4(0.6 * d), _up4(text_h + 0.32 * d))
    if shape == "document":
        return max(_g4(0.8 * d), _up4(text_h + 0.38 * d))
    if shape == "cylinder":
        return max(_g4(0.85 * d), _up4(text_h + 0.45 * d))
    return emblem_outline(shape, 0, 0, d)["h"]


def emblem_max_height(shape: str, d: float) -> float:
    """lib/emblem-shapes.ts:46 emblemMaxHeight()."""
    if shape in EMBLEM_FLEX:
        return _MAX_HEIGHT.get(shape, 1.6) * d
    return emblem_outline(shape, 0, 0, d)["h"]


def emblem_outline(shape: str, left: float, top: float, d: float, height: float | None = None) -> dict:
    """lib/emblem-shapes.ts:56-109 emblemOutline(). Returns a dict with keys h, textCy,
    anchor, box, and either points (polygon) or path (SVG path) or neither (circle)."""
    cx, right = left + d / 2, left + d

    def bbox(h: float) -> dict:
        return {"x": left, "y": top, "w": d, "h": h}

    def poly(h: float, text_cy: float, points: list[list[float]], anchor: dict | None = None) -> dict:
        return {"h": h, "textCy": text_cy, "points": points, "anchor": anchor if anchor is not None else bbox(h), "box": bbox(h)}

    if shape == "circle":
        return {"h": d, "textCy": d / 2, "anchor": bbox(d), "box": bbox(d)}
    if shape == "square":
        return poly(d, d / 2, [[left, top], [right, top], [right, top + d], [left, top + d]])
    if shape == "diamond":
        return poly(d, d / 2, [[cx, top], [right, top + d / 2], [cx, top + d], [left, top + d / 2]])
    if shape == "hexagon":
        q, m = _g4(0.25 * d), _g4(0.44 * d)
        return poly(2 * m, m, [[left, top + m], [cx - q, top], [cx + q, top], [right, top + m], [cx + q, top + 2 * m], [cx - q, top + 2 * m]])
    if shape == "triangle":
        h = _g4(0.9 * d)
        return poly(h, h - 0.2 * d, [[cx, top], [right, top + h], [left, top + h]], {"x": left + d / 4, "y": top, "w": d / 2, "h": h})
    if shape == "trapezoid":
        h, t = _g4(0.7 * d), _g4(0.2 * d)
        return poly(h, 0.6 * h, [[left + t, top], [right - t, top], [right, top + h], [left, top + h]], {"x": left + t / 2, "y": top, "w": d - t, "h": h})
    if shape == "inverted-trapezoid":
        h, t = _g4(0.7 * d), _g4(0.2 * d)
        return poly(h, 0.4 * h, [[left, top], [right, top], [right - t, top + h], [left + t, top + h]], {"x": left + t / 2, "y": top, "w": d - t, "h": h})
    if shape == "parallelogram":
        h = height if height is not None else _g4(0.6 * d)
        s = _g4(0.2 * d)
        return poly(h, h / 2, [[left + s, top], [right, top], [right - s, top + h], [left, top + h]], {"x": left + s / 2, "y": top, "w": d - s, "h": h})
    if shape == "pentagon-down":
        h, b = _g4(0.8 * d), _g4(0.5 * d)
        return poly(h, 0.26 * d, [[left, top], [right, top], [right, top + b], [cx, top + h], [left, top + b]])
    if shape == "pill":
        h = height if height is not None else d / 2
        r = h / 2
        n = js_num
        return {
            "h": h, "textCy": h / 2, "anchor": bbox(h), "box": bbox(h),
            "path": f"M{n(left + r)},{n(top)} H{n(right - r)} A{n(r)},{n(r)} 0 0 1 {n(right - r)},{n(top + h)} H{n(left + r)} A{n(r)},{n(r)} 0 0 1 {n(left + r)},{n(top)} Z",
        }
    if shape == "rounded":
        h = height if height is not None else _g4(0.7 * d)
        r = max(8, _g4(0.1 * d))
        n = js_num
        return {
            "h": h, "textCy": h / 2, "anchor": bbox(h), "box": bbox(h),
            "path": (
                f"M{n(left + r)},{n(top)} H{n(right - r)} A{n(r)},{n(r)} 0 0 1 {n(right)},{n(top + r)} V{n(top + h - r)} "
                f"A{n(r)},{n(r)} 0 0 1 {n(right - r)},{n(top + h)} H{n(left + r)} A{n(r)},{n(r)} 0 0 1 {n(left)},{n(top + h - r)} "
                f"V{n(top + r)} A{n(r)},{n(r)} 0 0 1 {n(left + r)},{n(top)} Z"
            ),
        }
    if shape == "cylinder":
        h = height if height is not None else _g4(0.85 * d)
        ry, rx = max(4, _g4(0.1 * d)), d / 2
        n = js_num
        return {
            "h": h, "textCy": (h + ry) / 2, "anchor": bbox(h), "box": bbox(h),
            "path": (
                f"M{n(left)},{n(top + ry)} A{n(rx)},{n(ry)} 0 0 1 {n(right)},{n(top + ry)} V{n(top + h - ry)} "
                f"A{n(rx)},{n(ry)} 0 0 1 {n(left)},{n(top + h - ry)} Z M{n(right)},{n(top + ry)} A{n(rx)},{n(ry)} 0 0 1 {n(left)},{n(top + ry)}"
            ),
        }
    if shape == "document":
        h = height if height is not None else _g4(0.8 * d)
        a = max(4, _g4(0.07 * d))
        b = top + h
        n = js_num
        return {
            "h": h, "textCy": (h - a) / 2, "anchor": bbox(h - a), "box": bbox(h),
            "path": f"M{n(left)},{n(top)} H{n(right)} V{n(b - a)} Q{n(right - d / 4)},{n(b - 3 * a)} {n(cx)},{n(b - a)} T{n(left)},{n(b - a)} Z",
        }
    raise ValueError(f"emblem_outline(): unknown shape {shape!r}")
