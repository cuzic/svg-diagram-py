"""1:1 port of lib/charts-harvey.ts's layoutHarvey() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the harvey() DSL constructor (lib/charts-dsl.ts's
harveyBand()) — defaults + the structural validations that affect layout.

harveyTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
the other chart kinds' *Texts() helpers.

Golden master: lib/charts-harvey.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .charts_base import Canvas, check_ids, check_text, common_chart_opts, fail, finite_num
from .emit_common import js_num, js_round


def resolve_harvey(rows_in: list, cols: list[str], values: list[list], opts: dict | None = None) -> dict:
    """lib/charts-harvey.ts:20-43 resolveHarvey()."""
    opts = opts or {}
    if not isinstance(rows_in, list) or len(rows_in) == 0:
        fail("harvey", "needs at least one row")
    rows = [r if isinstance(r, str) else r["label"] for r in rows_in]
    row_ids = [None if isinstance(r, str) else r.get("id") for r in rows_in]
    check_ids("harvey", row_ids, opts.get("id"))
    if not isinstance(cols, list) or len(cols) == 0:
        fail("harvey", "needs at least one column")
    if len(rows) > 20 or len(cols) > 10:
        fail("harvey", "is limited to 20 rows and 10 columns (it is a table of symbols to read at a glance)")
    for i, r in enumerate(rows):
        check_text("harvey", f"row {i + 1}", r)
    for i, c in enumerate(cols):
        check_text("harvey", f"column {i + 1}", c)
    if len(set(rows)) != len(rows) or len(set(cols)) != len(cols):
        fail("harvey", "row names and column names must each be unique")
    if not isinstance(values, list) or len(values) != len(rows):
        fail("harvey", f"values needs {len(rows)} rows (one per row name), got {len(values) if isinstance(values, list) else 'none'}")
    grid = []
    for i, r in enumerate(values):
        if not isinstance(r, list) or len(r) != len(cols):
            fail("harvey", f'row "{rows[i]}" needs {len(cols)} values (one per column), got {len(r) if isinstance(r, list) else "none"}')
        row_vals = []
        for j, v in enumerate(r):
            if v is None:
                row_vals.append(None)
                continue
            finite_num("harvey", f'"{rows[i]}" / "{cols[j]}"', v)
            if v not in (0, 1, 2, 3, 4):
                fail("harvey", f'"{rows[i]}" / "{cols[j]}" must be 0, 1, 2, 3 or 4 (quarters filled; null for not rated), got {v}')
            row_vals.append(v)
        grid.append(row_vals)
    levels = ["なし", "一部", "半分", "ほぼ", "十分"] if opts.get("levels") is None else list(opts["levels"])
    if len(levels) != 5:
        fail("harvey", "levels needs 5 names, from empty to full")
    for i, l in enumerate(levels):
        check_text("harvey", f"levels[{i}]", l)
    for h in opts.get("highlight") or []:
        if h not in cols:
            fail("harvey", f'highlight "{h}" is not a column name')
    return {"rows": rows, "rowIds": row_ids, "cols": list(cols), "values": grid, "levels": levels, "corner": opts.get("corner") or "", "highlight": list(opts.get("highlight") or [])}


def harvey_alt(s: dict) -> str:
    """lib/charts-harvey.ts:45-47 harveyAlt()."""
    level_desc = "、".join(f"{i}/4 = {l}" for i, l in enumerate(s["levels"]))
    rows_desc = []
    for i, r in enumerate(s["rows"]):
        cells = [f"{c} {'未評価' if s['values'][i][j] is None else s['levels'][s['values'][i][j]]}" for j, c in enumerate(s["cols"])]
        rows_desc.append(f"{r}: {'、'.join(cells)}")
    return f"ハーベイボール（{level_desc}）: {' / '.join(rows_desc)}"


def harvey_wedge(cx: float, cy: float, r: float, q: int) -> str:
    """lib/charts-harvey.ts:58-65 harveyWedge(): the path of a filled part, `q` quarters from
    12 o'clock clockwise."""

    def f(v: float) -> str:
        return js_num(js_round(v * 10) / 10)

    if q <= 0:
        return ""
    if q >= 4:
        return f"M{f(cx - r)},{f(cy)} a{js_num(r)},{js_num(r)} 0 1,0 {js_num(2 * r)},0 a{js_num(r)},{js_num(r)} 0 1,0 {js_num(-2 * r)},0 Z"
    a = q * math.pi / 2
    x = cx + r * math.sin(a)
    y = cy - r * math.cos(a)
    sweep = 1 if q > 2 else 0
    return f"M{f(cx)},{f(cy)} L{f(cx)},{f(cy - r)} A{js_num(r)},{js_num(r)} 0 {sweep},1 {f(x)},{f(y)} Z"


def _ball(c: Canvas, cx: float, cy: float, r: float, q: int, of: str | None = None) -> None:
    """lib/charts-harvey.ts:112-116 ball()."""

    def f(v: float) -> str:
        return js_num(js_round(v * 10) / 10)

    outline: dict = {"fill": "bg", "stroke": "text", "sw": 2}
    if of:
        outline["of"] = of
    c.path(f"M{f(cx - r)},{f(cy)} a{js_num(r)},{js_num(r)} 0 1,0 {js_num(2 * r)},0 a{js_num(r)},{js_num(r)} 0 1,0 {js_num(-2 * r)},0 Z", outline)
    if q > 0:
        fill: dict = {"fill": "text", "stroke": "text", "sw": 2}
        if of:
            fill["of"] = of
        c.path(harvey_wedge(cx, cy, r, q), fill)


def layout_harvey(s: dict, g: dict) -> dict:
    """lib/charts-harvey.ts:67-111 layoutHarvey()."""
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    lh = c.line_h()

    def r1(v: float) -> float:
        return js_round(v * 10) / 10

    r = max(12, math.ceil(size * 0.9))
    cell_h = 2 * r + 16
    row_w = min(max([c.tw(row) for row in s["rows"]] + ([c.tw(s["corner"])] if s["corner"] else [0])) + 16, g["w"] * 0.38)
    col_w = (g["w"] - row_w) / len(s["cols"])
    if col_w < 2 * r + 12:
        fail("harvey", f"{len(s['cols'])} columns do not fit in {js_round(g['w'])}px (raise width, or use fewer columns)")
    heads = [c.wrap(k, col_w - 8, k in s["highlight"]) for k in s["cols"]]
    rows_w = [c.wrap(row, row_w - 16) for row in s["rows"]]
    for i, ls in enumerate(heads):
        for l in ls:
            if c.tw(l, s["cols"][i] in s["highlight"]) > col_w - 4:
                fail("harvey", f'the column name "{s["cols"][i]}" is too long for {js_round(col_w)}px (shorten it, or raise width)')
    corner = c.wrap(s["corner"], row_w - 8) if s["corner"] else []
    head_h = max([len(corner)] + [len(l) for l in heads]) * lh + 12
    row_h = [max(cell_h, len(l) * lh + 10) for l in rows_w]
    body_t = g["y"] + head_h
    body_b = body_t + sum(row_h)
    legend_h = 2 * r + 18
    c.h = g["height"] if g.get("height") is not None else head_h + (body_b - body_t) + legend_h + 8
    if g.get("height") is not None and g["height"] < body_b - g["y"] + legend_h:
        fail("harvey", f"height {g['height']} is too small for {len(s['rows'])} rows (need at least {math.ceil(body_b - g['y'] + legend_h)})")
    left = g["x"] + row_w

    for j, k in enumerate(s["cols"]):
        if k in s["highlight"]:
            c.rect(r1(left + j * col_w + 2), g["y"], r1(col_w - 4), r1(body_b - g["y"]), {"fill": "accent", "op": 0.08, "stroke": "accent", "sw": 2})
    if corner:
        c.lines(corner, g["x"] + 4, g["y"] + head_h - 8 - (len(corner) - 1) * lh, "start", "muted")
    for j, k in enumerate(s["cols"]):
        hd = heads[j]
        c.lines(hd, left + (j + 0.5) * col_w, g["y"] + head_h - 8 - (len(hd) - 1) * lh, "middle", "text", {"bold": k in s["highlight"]})
    c.line(g["x"], body_t, g["x"] + g["w"], body_t, {"stroke": "text"})
    y = body_t
    for i in range(len(s["rows"])):
        rh = row_h[i]
        rw = rows_w[i]
        vrow = s["values"][i]
        rid = s["rowIds"][i]
        cy = y + rh / 2
        key = rid or f"#{i}"
        c.lines(rw, g["x"] + 4, cy - (len(rw) - 1) * lh / 2 + size * 0.36, "start", "text", {"bold": True, "of": key})
        if rid:
            c.anchors.append({"id": rid, "x": g["x"], "y": r1(y), "w": g["w"], "h": rh})
        for j in range(len(s["cols"])):
            cx = left + (j + 0.5) * col_w
            v = vrow[j]
            if v is None:
                c.text("—", cx, c.mid(cy), "middle", "muted", {"of": key})
                continue
            _ball(c, cx, cy, r, v, key)
        y += rh
        c.line(g["x"], y, g["x"] + g["w"], y, {"stroke": "text" if i == len(s["rows"]) - 1 else "border"})

    lr = js_round(r * 0.62)

    def item(t: str) -> float:
        return 2 * lr + 6 + c.tw(t)

    gap = 20
    lx = g["x"] + 4
    ly = body_b + 8 + lr + 4
    total = sum(item(t) + gap for t in s["levels"]) - gap
    if total > g["w"]:
        fail("harvey", "the legend does not fit (shorten the level names, or raise width)")
    for q, t in enumerate(s["levels"]):
        _ball(c, lx + lr, ly, lr, q)
        c.text(t, lx + 2 * lr + 6, c.mid(ly), "start", "text")
        lx += item(t) + gap

    return c.done()


def harvey_band(rows: list, cols: list[str], values: list[list], opts: dict | None = None) -> dict:
    """lib/charts-dsl.ts:131-134 harveyBand() + lib/dsl/charts.ts's harvey()."""
    opts = opts or {}
    spec = resolve_harvey(rows, cols, values, opts)
    alt = opts.get("alt") if opts.get("alt") is not None else harvey_alt(spec)
    band: dict = {"type": "chart", "kind": "harvey", "spec": spec, "alt": alt, "ids": [i for i in spec["rowIds"] if i]}
    band.update(common_chart_opts("harvey", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
    return band
