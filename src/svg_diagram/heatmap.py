"""1:1 port of lib/charts-heatmap.ts's layoutHeatmap() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the heatmap() DSL constructor (lib/charts-dsl.ts's
heatmapBand() + lib/dsl/charts.ts's heatmap()) — defaults + the structural validations that
affect layout, not every `check()`-style type validation (same scope decision as
flow_shapes.py's band constructors).

heatmapTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
wordArtTexts()/barsTexts(): this port measures per-call, not in a pre-pass.

Golden master: lib/charts-heatmap.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .charts_base import Canvas, ChartBand, check_text, common_chart_opts, decimals_in, fail, finite_num, ink_on_shade, nice_near, nice_up, num_text, shade_ops
from .charts_base import _to_precision as to_precision
from .emit_common import round1


def resolve_heatmap(rows: list[str], cols: list[str], values: list[list[float | None]], opts: dict) -> dict:
    """lib/charts-heatmap.ts:30-57 resolveHeatmap()."""
    if not rows or not cols:
        fail("heatmap", "needs at least one row and one column")
    if len(rows) > 40 or len(cols) > 24:
        fail("heatmap", f"{len(rows)} rows x {len(cols)} columns is too large for one figure (at most 40 x 24)")
    for i, r in enumerate(rows):
        check_text("heatmap", f"row {i + 1}'s label", r)
    for i, c in enumerate(cols):
        check_text("heatmap", f"column {i + 1}'s label", c)
    if len(values) != len(rows):
        fail("heatmap", f"values has {len(values)} rows for {len(rows)} row labels")
    for i, r in enumerate(values):
        if not isinstance(r, list) or len(r) != len(cols):
            fail("heatmap", f'row "{rows[i]}" has {len(r) if isinstance(r, list) else 0} values for {len(cols)} columns (use null for an empty cell)')
    flat: list[float | None] = []
    k = 0
    for row in values:
        for v in row:
            if v is None:
                flat.append(None)
            else:
                flat.append(finite_num("heatmap", f'the value of "{rows[k // len(cols)]}" x "{cols[k % len(cols)]}"', v))
            k += 1
    real = [v for v in flat if v is not None]
    if not real:
        fail("heatmap", "every cell is null: there is nothing to show")
    levels = opts.get("levels") if opts.get("levels") is not None else 5
    if not (isinstance(levels, int) and not isinstance(levels, bool) and 3 <= levels <= 6):
        fail("heatmap", f"levels must be a whole number from 3 to 6 (got {levels})")
    min_v = opts.get("min") if opts.get("min") is not None else min(real)
    max_v = opts.get("max") if opts.get("max") is not None else max(real)
    if opts.get("min") is None and opts.get("max") is None and max_v > min_v:
        step = nice_near((max_v - min_v) / levels)

        def lo(st: float) -> float:
            return math.floor(min_v / st + 1e-9) * st

        while math.ceil((max_v - lo(step)) / step - 1e-9) > 6:
            step = nice_up(step * 1.01)
        min_v = to_precision(lo(step), 12)
        levels = max(3, math.ceil((max_v - min_v) / step - 1e-9))
        max_v = to_precision(min_v + levels * step, 12)
    finite_num("heatmap", "min", min_v)
    finite_num("heatmap", "max", max_v)
    if max_v == min_v:
        max_v = min_v + 1
    if not (max_v > min_v):
        fail("heatmap", f"max ({max_v}) must be above min ({min_v})")
    decimals = opts.get("decimals")
    if decimals is not None and not (isinstance(decimals, int) and not isinstance(decimals, bool) and 0 <= decimals <= 6):
        fail("heatmap", f"decimals must be a whole number from 0 to 6 (got {decimals})")
    if decimals is None:
        decimals = min(2, max([0] + [decimals_in(v) for v in real]))
    spec: dict = {
        "rows": list(rows), "cols": list(cols), "values": [list(r) for r in values],
        "unit": opts.get("unit") or "", "decimals": decimals, "min": min_v, "max": max_v, "levels": levels,
        "rowHeader": opts.get("rowHeader") is not False, "corner": opts.get("corner") or "", "scale": opts.get("scale") is not False,
    }
    if opts.get("cellH") is not None:
        spec["cellH"] = opts["cellH"]
    return spec


def _to_fixed_num(v: float, d: int) -> float:
    factor = 10**d
    r = math.floor(abs(v) * factor + 0.5) / factor
    return r if v >= 0 else -r


def _cell_text(v: float, s: dict) -> str:
    return f"{num_text(_to_fixed_num(v, s['decimals']))}{s['unit']}"


def _bound(i: int, s: dict) -> float:
    return s["min"] + (s["max"] - s["min"]) * i / s["levels"]


def _range_text(i: int, s: dict) -> str:
    def f(v: float) -> str:
        return num_text(to_precision(v, 6))

    if i == 0:
        return f"〜{f(_bound(1, s))}"
    if i == s["levels"] - 1:
        return f"{f(_bound(i, s))}〜"
    return f"{f(_bound(i, s))}〜{f(_bound(i + 1, s))}"


def heat_level(v: float, s: dict) -> int:
    """lib/charts-heatmap.ts:64 heatLevel()."""
    return max(0, min(s["levels"] - 1, math.floor((v - s["min"]) / (s["max"] - s["min"]) * s["levels"] + 1e-9)))


def heatmap_alt(s: dict) -> str:
    """lib/charts-heatmap.ts:66-69 heatmapAlt()."""
    rows = []
    for i, r in enumerate(s["rows"]):
        vals = " / ".join("-" if v is None else _cell_text(v, s) for v in s["values"][i])
        rows.append(f"{r}: {vals}")
    return f"ヒートマップ（列: {'、'.join(s['cols'])}）。{'。'.join(rows)}"


def layout_heatmap(s: dict, g: dict) -> dict:
    """lib/charts-heatmap.ts:81-145 layoutHeatmap()."""
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    row_tw = max([c.tw(r, s["rowHeader"]) for r in s["rows"]] + ([c.tw(s["corner"], True) / 2] if s["corner"] else [0]))
    row_w = min(row_tw + 20, g["w"] * 0.3)
    plot_l = g["x"] + row_w
    cell_w = (g["x"] + g["w"] - plot_l) / len(s["cols"])
    lh = c.line_h()
    row_ls = [c.wrap(r, row_w - 8, s["rowHeader"]) for r in s["rows"]]
    for i, ls in enumerate(row_ls):
        for l in ls:
            if c.tw(l, s["rowHeader"]) > row_w - 4:
                fail("heatmap", f'the row label "{s["rows"][i]}" is too long for its column {math.floor(row_w)}px wide (shorten it, or raise width)')
    row_need = max(len(ls) for ls in row_ls) * lh + 8
    cell_h = s.get("cellH") if s.get("cellH") is not None else max(size + 16, 32, row_need)
    if s.get("cellH") is not None and not (s["cellH"] >= max(size + 8, row_need)):
        fail("heatmap", f'cellH {s["cellH"]} is too small for the {size}px text of its rows (at least {max(size + 8, row_need)})')
    texts = [[("–" if v is None else _cell_text(v, s)) for v in row] for row in s["values"]]
    widest = max(c.tw(t, True) for row in texts for t in row)
    if widest > cell_w - 8:
        fail("heatmap", f"the numbers (up to {math.ceil(widest)}px) do not fit in cells {math.floor(cell_w)}px wide (raise width, use fewer columns, or drop the unit)")
    heads = [c.wrap(col, cell_w - 6, True) for col in s["cols"]]
    for i, h in enumerate(heads):
        for l in h:
            if c.tw(l, True) > cell_w - 4:
                fail("heatmap", f'the column label "{s["cols"][i]}" is too long for cells {math.floor(cell_w)}px wide (shorten it, or raise width)')
    head_h = max([len(h) for h in heads] + ([len(c.wrap(s["corner"], row_w - 12, True))] if s["corner"] else [1])) * lh + 10
    ops = shade_ops(s["levels"])
    body_t = g["y"] + head_h
    gap = 2
    legend: list[dict] = []
    legend_h = 0.0
    if s["scale"]:
        sw = 22
        items = [{"level": i, "text": _range_text(i, s)} for i in range(s["levels"])]
        lx = g["x"] + c.tw("凡例") + 14
        ly = 0.0
        for it in items:
            w = sw + 6 + c.tw(it["text"]) + 18
            if lx + w - 18 > g["x"] + g["w"] and lx > g["x"] + c.tw("凡例") + 14:
                lx = g["x"]
                ly += lh + 6
            legend.append({"x": lx, "y": ly, **it})
            lx += w
        legend_h = ly + size + 14 + 8
    c.h = g["height"] if g.get("height") is not None else head_h + len(s["rows"]) * cell_h + (legend_h + 6 if s["scale"] else 0) + 4
    if g.get("height") is not None and g["height"] < head_h + len(s["rows"]) * cell_h + legend_h:
        fail("heatmap", f'height {g["height"]} is too small for {len(s["rows"])} rows (need at least {head_h + len(s["rows"]) * cell_h + legend_h})')

    r1 = round1

    if s["corner"]:
        corner_lines = c.wrap(s["corner"], row_w - 12, True)
        c.lines(corner_lines, g["x"] + 4, g["y"] + head_h - 8 - (len(corner_lines) - 1) * lh, "start", "muted", {"bold": True})
    for i, h in enumerate(heads):
        c.lines(h, plot_l + (i + 0.5) * cell_w, g["y"] + head_h - 8 - (len(h) - 1) * lh, "middle", "text", {"bold": True})
    for i, r in enumerate(s["rows"]):
        y = body_t + i * cell_h
        cy = y + cell_h / 2
        c.lines(row_ls[i], g["x"] + 4, c.mid(cy) - (len(row_ls[i]) - 1) * lh / 2, "start", "text", {"bold": s["rowHeader"]})
        for j, v in enumerate(s["values"][i]):
            x = plot_l + j * cell_w
            t = texts[i][j]
            if v is None:
                host = c.rect(r1(x + gap / 2), r1(y + gap / 2), r1(cell_w - gap), r1(cell_h - gap), {"fill": "none", "stroke": "border", "sw": 2, "dash": "3,3", "solid": f"cell {r} x {s['cols'][j]}"})
                c.text(t, x + cell_w / 2, c.mid(cy), "middle", "muted", {"host": host})
                continue
            op = ops[heat_level(v, s)]
            ink = ink_on_shade(op)
            host = c.rect(r1(x + gap / 2), r1(y + gap / 2), r1(cell_w - gap), r1(cell_h - gap), {"fill": "accent", "op": op, "solid": f"cell {r} x {s['cols'][j]}"})
            c.text(t, x + cell_w / 2, c.mid(cy), "middle", ink, {"bold": True, "host": host, "on": {"fill": "accent", "op": op, "ink": ink}})
    if s["rowHeader"]:
        c.line(r1(plot_l - 2), r1(body_t), r1(plot_l - 2), r1(body_t + len(s["rows"]) * cell_h), {"stroke": "border"})
    if s["scale"]:
        top = body_t + len(s["rows"]) * cell_h + 14
        c.text("凡例", g["x"], c.mid(top + 7), "start", "muted", {})
        for l in legend:
            y = top + l["y"]
            c.rect(r1(l["x"]), r1(y), 22, 14, {"fill": "accent", "op": ops[l["level"]], "stroke": "accent", "sw": 2})
            c.text(l["text"], l["x"] + 28, c.mid(y + 7), "start", "text")
    return c.done()


def heatmap_band(rows: list[str], cols: list[str], values: list[list[float | None]], opts: dict | None = None) -> ChartBand:
    """lib/charts-dsl.ts:61-64 heatmapBand() + lib/dsl/charts.ts:125-127 heatmap()."""
    opts = opts or {}
    spec = resolve_heatmap(rows, cols, values, opts)
    alt = opts.get("alt") if opts.get("alt") is not None else heatmap_alt(spec)
    return ChartBand(kind="heatmap", spec=spec, alt=alt, **common_chart_opts("heatmap", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
