"""1:1 port of lib/charts-butterfly.ts's layoutButterfly() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the butterfly() DSL constructor (lib/charts-dsl.ts's
butterflyBand()) — defaults + the structural validations that affect layout.

butterflyTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
the other chart kinds' *Texts() helpers.

Golden master: lib/charts-butterfly.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .charts_base import Canvas, ChartBand, check_ids, check_text, common_chart_opts, fail, finite_num, num_text
from .emit_common import round1


def resolve_butterfly(rows: list[dict], opts: dict) -> dict:
    """lib/charts-butterfly.ts:28-41 resolveButterfly()."""
    if not isinstance(rows, list) or len(rows) == 0:
        fail("butterfly", "needs at least one row")
    if len(rows) > 20:
        fail("butterfly", f"{len(rows)} rows are too many for one figure (at most 20)")
    if opts.get("leftLabel") is None or opts.get("rightLabel") is None:
        fail("butterfly", 'needs the names of both groups: butterfly(rows, {leftLabel: "自社", rightLabel: "競合"})')
    check_ids("butterfly", [r.get("id") for r in rows], opts.get("id"))
    lst = []
    for k, r in enumerate(rows):
        item: dict = {
            "label": check_text("butterfly", f"row {k + 1}'s label", r["label"]),
            "left": finite_num("butterfly", f'"{r["label"]}" left', r["left"], min=0),
            "right": finite_num("butterfly", f'"{r["label"]}" right', r["right"], min=0),
        }
        if r.get("id") is not None:
            item["id"] = r["id"]
        lst.append(item)
    if len({r["label"] for r in lst}) != len(lst):
        fail("butterfly", "each row needs its own label")
    if all(r["left"] == 0 and r["right"] == 0 for r in lst):
        fail("butterfly", "all values are 0")
    sort = opts.get("sort") or "given"
    if sort not in ("given", "left", "right"):
        fail("butterfly", f"sort must be given, left or right (got {sort})")
    if sort == "given":
        ordered = lst
    else:
        indexed = list(enumerate(lst))
        indexed.sort(key=lambda p: (-p[1][sort], p[0]))
        ordered = [p[1] for p in indexed]
    tones = ("accent", "danger", "muted", "text")
    for k in ("leftTone", "rightTone"):
        if opts.get(k) is not None and opts[k] not in tones:
            fail("butterfly", f"{k} must be accent, danger, muted or text")
    return {
        "rows": ordered,
        "leftLabel": check_text("butterfly", "leftLabel", opts["leftLabel"]),
        "rightLabel": check_text("butterfly", "rightLabel", opts["rightLabel"]),
        "unit": opts.get("unit") or "",
        "leftTone": opts.get("leftTone") or "text",
        "rightTone": opts.get("rightTone") or "accent",
    }


def butterfly_alt(s: dict) -> str:
    """lib/charts-butterfly.ts:43-45 butterflyAlt()."""
    parts = [f"{r['label']} {num_text(r['left'])}{s['unit']} 対 {num_text(r['right'])}{s['unit']}" for r in s["rows"]]
    return f"バタフライチャート（左: {s['leftLabel']}、右: {s['rightLabel']}）: {'、'.join(parts)}"


def layout_butterfly(s: dict, g: dict) -> dict:
    """lib/charts-butterfly.ts:52-99 layoutButterfly()."""
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    line_h = c.line_h()

    r1 = round1

    def v_text(v: float) -> str:
        return f"{num_text(v)}{s['unit']}"

    val_w = max(max(c.tw(v_text(r["left"]), True), c.tw(v_text(r["right"]), True)) for r in s["rows"]) + 10
    label_w = min(max(c.tw(r["label"]) for r in s["rows"]) + 24, g["w"] * 0.3)
    plot_w = (g["w"] - label_w) / 2 - val_w - 4
    if plot_w < 70:
        fail("butterfly", "the figure is too narrow for its labels (raise width, or shorten the labels / unit)")
    inner_l = g["x"] + val_w + 4 + plot_w
    inner_r = inner_l + label_w
    outer_l = g["x"] + val_w + 4
    outer_r = inner_r + plot_w
    max_v = max(v for r in s["rows"] for v in (r["left"], r["right"]))
    bar_h = max(24, size + 10)
    wrapped = [c.wrap(r["label"], label_w - 16) for r in s["rows"]]
    row_h = [max(bar_h + 12, len(l) * line_h + 8) for l in wrapped]
    head_h = size + 18
    y0 = g["y"] + head_h
    row_h_total = sum(row_h)
    c.h = g["height"] if g.get("height") is not None else head_h + row_h_total + 4
    if g.get("height") is not None and g["height"] < head_h + row_h_total:
        fail("butterfly", f"height {g['height']} is too small for {len(s['rows'])} rows (need at least {head_h + row_h_total})")
    body_b = y0 + row_h_total
    sw = 14
    for name, tone, a, b in (
        (s["leftLabel"], s["leftTone"], outer_l, inner_l),
        (s["rightLabel"], s["rightTone"], inner_r, outer_r),
    ):
        need = sw + 6 + c.tw(name, True)
        if need > b - a + val_w:
            fail("butterfly", f'the group name "{name}" is wider than its half (shorten it, or raise width)')
        x = r1((a + b) / 2 - need / 2)
        cy = g["y"] + max(4 + sw / 2, math.ceil(size * 0.64))
        c.rect(x, cy - sw / 2, sw, sw, {"fill": tone})
        c.text(name, x + sw + 6, c.mid(cy), "start", "text", {"bold": True})

    c.line(r1(inner_l), y0, r1(inner_l), body_b, {"stroke": "border"})
    c.line(r1(inner_r), y0, r1(inner_r), body_b, {"stroke": "border"})

    y = y0
    for k, row in enumerate(s["rows"]):
        lns = wrapped[k]
        rh = row_h[k]
        cy = y + rh / 2
        top = cy - bar_h / 2
        key = row.get("id") or f"#{k}"
        c.lines(lns, (inner_l + inner_r) / 2, cy - (len(lns) - 1) * line_h / 2 + size * 0.36, "middle", "text", {"of": key})
        sides = [
            {"v": row["left"], "tone": s["leftTone"], "name": s["leftLabel"], "x1": inner_l - row["left"] / max_v * plot_w, "x2": inner_l, "out": "end"},
            {"v": row["right"], "tone": s["rightTone"], "name": s["rightLabel"], "x1": inner_r, "x2": inner_r + row["right"] / max_v * plot_w, "out": "start"},
        ]
        for b in sides:
            w = b["x2"] - b["x1"]
            if w >= 1:
                c.rect(r1(b["x1"]), r1(top), r1(w), bar_h, {"fill": b["tone"], "solid": f"{row['label']} {b['name']}", "of": key})
            text = v_text(b["v"])
            tx = b["x1"] - 6 if b["out"] == "end" else b["x2"] + 6
            cand_x = tx if w >= 1 else (inner_l - 6 if b["out"] == "end" else inner_r + 6)
            tone_pick = "text" if b["tone"] == "muted" else b["tone"]
            if not c.place(text, [{"x": cand_x, "y": c.mid(cy), "anchor": b["out"]}], tone_pick, {"bold": True, "of": key}):
                fail("butterfly", f'the value "{text}" of "{row["label"]}" has no room')
        sl, sr = sides
        if row.get("id"):
            c.anchors.append({"id": row["id"], "x": r1(sl["x1"]), "y": r1(top), "w": r1(sr["x2"] - sl["x1"]), "h": bar_h})
        y += rh

    return c.done()


def butterfly_band(rows: list[dict], opts: dict) -> ChartBand:
    """lib/charts-dsl.ts:121-124 butterflyBand() + lib/dsl/charts.ts's butterfly()."""
    spec = resolve_butterfly(rows, opts)
    alt = opts.get("alt") if opts.get("alt") is not None else butterfly_alt(spec)
    return ChartBand(kind="butterfly", spec=spec, alt=alt, **common_chart_opts("butterfly", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
