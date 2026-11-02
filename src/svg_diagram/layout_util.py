"""1:1 port of the pure-arithmetic parts of lib/layout-util.ts: box/badge/icon/tag/stamp/legend
geometry constants, and the row()/grid() width-distribution algorithm (gridColumns/
rowChildGeometry/gridChildGeometry/colSlots) — "pure arithmetic, no text metrics needed"
per the Node comment, so (unlike cloud()/mindmap()/cause()) this is byte-identical to
Node.js, not an approximation.

Golden master: lib/layout-util.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .emit_common import js_round

# ---- geometry constants (lib/layout-util.ts:9-47) --------------------------------------


def boundary_chip_h(note: float) -> float:
    return math.ceil(note * 1.4) + 6


LINE_HEIGHT_EM = 1.4
BOX_PAD_X = 20
BOX_PAD_Y = 16
BOX_INNER_GAP = 8

STEP_BADGE_R = 15
STEP_BADGE_GAP = 10
STEP_BADGE_BASELINE_OFFSET = 6
STEP_INDENT = 2 * STEP_BADGE_R + STEP_BADGE_GAP

ICON_SIZE = 32
ICON_INDENT = ICON_SIZE + 12
ICON_H = ICON_SIZE
TOP_ICON_SIZE = 48
TOP_ICON_GAP = 8

TAG_H = 24
TAG_PAD_X = 8
CANVAS_MIN_REGION_W = 96
STAMP_H, STAMP_GAP = 24, 6
STAMP_PAD_X = 6

LEGEND_SWATCH_W, LEGEND_ITEM_GAP, LEGEND_ROW_H = 36, 28, 24

SWIMLANE_COMFY_COL = 112

GRID = 4


def _ceil_grid(n: float) -> float:
    return math.ceil(n / GRID - 1e-9) * GRID


def _round_grid(n: float) -> float:
    return js_round(n / GRID) * GRID


snap_grid = _round_grid


def col_slots(children: list[dict]) -> list[dict]:
    """lib/layout-util.ts:56-59 colSlots()."""
    out = []
    nxt = 1
    for c in children:
        span = c.get("span", 1)
        col = c.get("col", nxt)
        out.append({"col": col, "span": span})
        nxt = col + span
    return out


def _bump(a: list[float], i: int, by: float = 1) -> None:
    """lib/layout-util.ts:86 bump(): writes outside [0, len(a)) are a no-op, matching JS
    `a[i] = (a[i] ?? NaN) + by` on a negative/out-of-range index (a non-array-index
    property write that never touches the array's real elements)."""
    if 0 <= i < len(a):
        a[i] += by


def grid_columns(content_width: float, n: int, gap: float, *, fixed_gap: bool = False, center_gutter: bool = False, any_gap: bool = False) -> dict | None:
    """lib/layout-util.ts:88-114 gridColumns()."""
    g0 = (gap if fixed_gap else _ceil_grid(max(gap, 0))) if n > 1 else 0
    units = math.floor((content_width - (n - 1) * g0) / GRID + 1e-9)
    if units < n:
        return None
    base = math.floor(units / n)
    extra = units - base * n
    gutter = [g0] * max(n - 1, 0)
    add = [0.0] * n
    if n > 1 and extra == n - 1 and not fixed_gap and (any_gap or GRID <= 0.25 * g0):
        for k in range(n - 1):
            _bump(gutter, k, GRID)
        extra = 0
    odd = extra % 2 == 1
    extra -= 1 if odd else 0
    pairs = extra / 2
    half = math.floor(n / 2)
    for j in range(int(pairs)):
        i = min(half - 1, math.floor((j + 0.5) * half / pairs))
        _bump(add, i)
        _bump(add, n - 1 - i)
    if odd:
        mid = (n - 1) / 2
        if n % 2 == 1 and add[int(mid)] == 0:
            _bump(add, int(mid))
        elif n % 2 == 0 and center_gutter and not fixed_gap and (any_gap or GRID <= 0.25 * g0):
            _bump(gutter, n // 2 - 1, GRID)
        else:
            idx = next((k for k, v in enumerate(add) if v == 0), -1)
            _bump(add, idx)
    w = [(base + v) * GRID for v in add]
    x: list[float] = []
    at = 0.0
    for k, v in enumerate(w):
        x.append(at)
        at += v + (gutter[k] if k < n - 1 else 0)
    return {"x": x, "w": w}


def row_child_geometry(band: dict, content_width: float) -> dict:
    """lib/layout-util.ts:116-179 rowChildGeometry()."""
    children = band["children"]
    n = len(children)
    gap = band["gap"]

    if band.get("cols"):
        cols = band["cols"]
        grid = grid_columns(content_width, cols, gap, center_gutter=(cols == 12))
        cw = (content_width - (cols - 1) * gap) / cols

        def col_x(c: int) -> float:
            return grid["x"][c] if grid else c * (cw + gap)

        def col_w(c: int) -> float:
            return grid["w"][c] if grid else cw

        nxt = 1
        widths, x_offsets = [], []
        for c in children:
            span = c.get("span", 1)
            col = c.get("col", nxt)
            if col < 1 or col + span - 1 > cols:
                name = c.get("title") or c.get("id") or "(box)"
                raise ValueError(f"row({{cols: {cols}}}): child \"{name}\" at col {col} span {span} falls outside the {cols} columns")
            first, last = col - 1, col + span - 2
            widths.append(col_x(last) + col_w(last) - col_x(first))
            x_offsets.append(col_x(first))
            nxt = col + span
        return {"widths": widths, "xOffsets": x_offsets}

    if band.get("justify") == "stretch":
        flex0 = children[0].get("flex", 1) if children else 1
        equal = all(c.get("flex", 1) == flex0 for c in children)
        if equal and n > 0:
            grid = grid_columns(content_width, n, gap)
            if grid:
                return {"widths": grid["w"], "xOffsets": grid["x"]}
        elif n > 0:
            g = _ceil_grid(max(gap, 0)) if n > 1 else 0
            avail = content_width - (n - 1) * g
            flex_sum = sum(c.get("flex", 1) for c in children)
            widths, x_offsets = [], []
            x, ok, cum = 0.0, avail > 0, 0.0
            for i, c in enumerate(children):
                cum += c.get("flex", 1)
                if i == n - 1:
                    right = math.floor(content_width / GRID + 1e-9) * GRID
                else:
                    right = _round_grid(avail * cum / flex_sum + i * g)
                if right - x < GRID:
                    ok = False
                x_offsets.append(x)
                widths.append(right - x)
                x = right + g
            if ok:
                return {"widths": widths, "xOffsets": x_offsets}
        avail = content_width - (n - 1) * gap
        flex_sum = sum(c.get("flex", 1) for c in children)
        widths = [avail * c.get("flex", 1) / flex_sum for c in children]
        x_offsets = []
        x = 0.0
        for w in widths:
            x_offsets.append(x)
            x += w + gap
        return {"widths": widths, "xOffsets": x_offsets}

    # fixed-width children, block start- or center-aligned
    widths = [c.get("width", band.get("itemWidth", 160)) for c in children]
    block_width = sum(widths) + (n - 1) * gap
    start = (content_width - block_width) / 2 if band.get("justify") == "center" else 0
    x_offsets = []
    x = start
    for w in widths:
        x_offsets.append(x)
        x += w + gap
    return {"widths": widths, "xOffsets": x_offsets}


def stamp_chip_w(width_of, text: str, note_size: float) -> float:
    """lib/layout-util.ts:46 stampChipW()."""
    from .atoms import text_width

    return text_width(width_of, text, note_size, 400) + 2 * STAMP_PAD_X


def grid_child_geometry(band: dict, content_width: float) -> dict:
    """lib/layout-util.ts:181-187 gridChildGeometry()."""
    cols, gap = band["cols"], band["gap"]
    grid = grid_columns(content_width, cols, gap)
    cell_width = (content_width - (cols - 1) * gap) / cols
    xs = grid["x"] if grid else [j * (cell_width + gap) for j in range(cols)]
    ws = grid["w"] if grid else [cell_width] * cols
    return {"xs": xs, "ws": ws}
