"""1:1 port of lib/charts-tornado.ts's layoutTornado() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the tornado() DSL constructor (lib/charts-dsl.ts's
tornadoBand()) — defaults + the structural validations that affect layout.

tornadoTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
the other chart kinds' *Texts() helpers.

Golden master: lib/charts-tornado.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import json
import math

from .charts_base import Canvas, check_domain, check_ids, check_inset, check_text, common_chart_opts, fail, finite_num, inset_or_need, num_text, thin_ticks, value_scale
from .emit_common import js_round


def tornado_scale(s: dict) -> dict:
    """lib/charts-tornado.ts:39-42 tornadoScale()."""
    all_vals = [v for i in s["items"] for v in (i["low"], i["high"])]
    lo = min([s["base"], *all_vals])
    hi = max([s["base"], *all_vals])
    return value_scale("tornado", lo, hi, s.get("domain"))


def resolve_tornado(items: list[dict], opts: dict) -> dict:
    """lib/charts-tornado.ts:44-59 resolveTornado()."""
    if not isinstance(items, list) or len(items) == 0:
        fail("tornado", "needs at least one item")
    if len(items) > 24:
        fail("tornado", f"{len(items)} items are too many for one figure (at most 24: keep the ones that matter)")
    if opts.get("base") is None:
        fail("tornado", "needs the base result: tornado(items, {base: 1000})")
    base = finite_num("tornado", "base", opts["base"])
    check_ids("tornado", [i.get("id") for i in items], opts.get("id"))
    lst = []
    for k, i in enumerate(items):
        item: dict = {
            "label": check_text("tornado", f"item {k + 1}'s label", i["label"]),
            "low": finite_num("tornado", f'"{i["label"]}" low', i["low"]),
            "high": finite_num("tornado", f'"{i["label"]}" high', i["high"]),
        }
        if i.get("id") is not None:
            item["id"] = i["id"]
        lst.append(item)
    if opts.get("sort") is False:
        ordered = lst
    else:
        indexed = list(enumerate(lst))
        indexed.sort(key=lambda p: (-abs(p[1]["high"] - p[1]["low"]), p[0]))
        ordered = [p[1] for p in indexed]
    tones = ("accent", "danger", "muted", "text")
    for k in ("lowTone", "highTone"):
        if opts.get(k) is not None and opts[k] not in tones:
            fail("tornado", f"{k} must be accent, danger, muted or text")
    if opts.get("axisGroup") is not None and opts["axisGroup"] is not False:
        fail("tornado", f"axisGroup must be false (this chart's axis is its own) or left out (got {json.dumps(opts['axisGroup'])})")
    domain = check_domain("tornado", opts.get("domain"))
    plot_inset = check_inset("tornado", opts.get("plotInset"))
    spec: dict = {
        "items": ordered, "base": base, "unit": opts.get("unit") or "",
        "lowLabel": opts.get("lowLabel") or "低ケース", "highLabel": opts.get("highLabel") or "高ケース",
        "baseLabel": opts.get("baseLabel") or "基準", "lowTone": opts.get("lowTone") or "text", "highTone": opts.get("highTone") or "accent",
    }
    if domain:
        spec["domain"] = domain
    if plot_inset:
        spec["plotInset"] = plot_inset
    if opts.get("axisGroup") is False:
        spec["axisGroup"] = False
    tornado_scale(spec)
    return spec


def tornado_alt(s: dict) -> str:
    """lib/charts-tornado.ts:60-62 tornadoAlt()."""
    parts = [f"{i['label']} {s['lowLabel']} {num_text(i['low'])}{s['unit']}・{s['highLabel']} {num_text(i['high'])}{s['unit']}" for i in s["items"]]
    return f"トルネード図（{s['baseLabel']} {num_text(s['base'])}{s['unit']}）: {'、'.join(parts)}"


def layout_tornado(s: dict, g: dict) -> dict:
    """lib/charts-tornado.ts:70-138 layoutTornado()."""
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    sc = tornado_scale(s)

    def v_text(v: float) -> str:
        return f"{num_text(v)}{s['unit']}"

    label_w = min(max(c.tw(i["label"]) for i in s["items"]) + 14, g["w"] * 0.34)
    val_w = max(max(c.tw(v_text(i["low"]), True), c.tw(v_text(i["high"]), True)) for i in s["items"]) + 10
    inset_l, inset_r = inset_or_need("tornado", s.get("plotInset"), label_w + val_w + 4, val_w + 8)
    plot_l = g["x"] + inset_l
    plot_r = g["x"] + g["w"] - inset_r
    if plot_r - plot_l < 120:
        fail("tornado", "the figure is too narrow for its labels (raise width, or shorten the labels / unit)")

    def x_of(v: float) -> float:
        return plot_l + (v - sc["min"]) / (sc["max"] - sc["min"]) * (plot_r - plot_l)

    bar_h = max(24, size + 10)
    pitch = bar_h + 12
    line_h = c.line_h()
    wrapped = [c.wrap(i["label"], label_w - 14) for i in s["items"]]

    def same_side(i: dict) -> bool:
        return (i["low"] - s["base"]) * (i["high"] - s["base"]) > 0

    row_h = [max(2 * pitch - 8 if same_side(s["items"][k]) else pitch, len(l) * line_h + 8) for k, l in enumerate(wrapped)]

    sw = 14

    def item_w(t: str) -> float:
        return sw + 6 + c.tw(t)

    for t in (s["lowLabel"], s["highLabel"]):
        if item_w(t) > g["w"]:
            fail("tornado", f'the legend name "{t}" is wider than the figure (shorten lowLabel / highLabel, or raise width)')
    legend_at: list[dict] = []
    lx = min(plot_l, g["x"] + g["w"] - item_w(s["lowLabel"]))
    row = 0
    for t in (s["lowLabel"], s["highLabel"]):
        if legend_at and lx + item_w(t) > g["x"] + g["w"]:
            lx = min(plot_l, g["x"] + g["w"] - item_w(t))
            row += 1
        legend_at.append({"x": lx, "row": row})
        lx += item_w(t) + 22
    legend_rows = legend_at[-1]["row"] + 1
    head_h = (size + 12) * (legend_rows + 1) + 8
    axis_h = size + 16
    y0 = g["y"] + head_h
    row_h_total = sum(row_h)
    c.h = g["height"] if g.get("height") is not None else max(160, head_h + row_h_total + axis_h + 4)
    if g.get("height") is not None and g["height"] < head_h + row_h_total + axis_h:
        fail("tornado", f"height {g['height']} is too small for {len(s['items'])} rows (need at least {head_h + row_h_total + axis_h})")
    body_b = y0 + row_h_total

    def r1(v: float) -> float:
        return js_round(v * 10) / 10

    for i, (tone, text) in enumerate(((s["lowTone"], s["lowLabel"]), (s["highTone"], s["highLabel"]))):
        la = legend_at[i]
        cy = g["y"] + la["row"] * (size + 12) + max(4 + sw / 2, math.ceil(size * 0.64))
        c.rect(la["x"], cy - sw / 2, sw, sw, {"fill": tone})
        c.text(text, la["x"] + sw + 6, c.mid(cy), "start", "text")

    tk = [{"v": v} for v in sc["ticks"]]
    shown = thin_ticks(tk, x_of, lambda t: c.tw(num_text(t["v"])), 12)
    for t in tk:
        c.line(x_of(t["v"]), y0, x_of(t["v"]), body_b, {"stroke": "border"})
        if t in shown:
            c.text(num_text(t["v"]), x_of(t["v"]), body_b + size + 8, "middle", "muted")

    y = y0
    for k, it in enumerate(s["items"]):
        cy = y + row_h[k] / 2
        top = cy - bar_h / 2
        key = it.get("id") or f"#{k}"
        c.lines(wrapped[k], g["x"] + label_w - 10, cy - (len(wrapped[k]) - 1) * line_h / 2 + size * 0.36, "end", "text", {"of": key})
        xb = x_of(s["base"])
        same = same_side(it)
        bars = [{"v": it["low"], "tone": s["lowTone"], "name": s["lowLabel"]}, {"v": it["high"], "tone": s["highTone"], "name": s["highLabel"]}]
        geom = []
        for j, b in enumerate(bars):
            x1 = min(xb, x_of(b["v"]))
            x2 = max(xb, x_of(b["v"]))
            by = cy - bar_h - 2 + j * (bar_h + 4) if same else top
            if x2 - x1 >= 1:
                c.rect(r1(x1), r1(by), r1(x2 - x1), r1(bar_h), {"fill": b["tone"], "solid": f"{it['label']} {b['name']}", "of": key})
            geom.append({"x1": x1, "x2": x2, "by": by})
        if it.get("id"):
            x1 = min(xb - 1, *[q["x1"] for q in geom])
            x2 = max(xb + 1, *[q["x2"] for q in geom])
            y1 = min(q["by"] for q in geom)
            y2 = max(q["by"] for q in geom) + bar_h
            c.anchors.append({"id": it["id"], "x": r1(x1), "y": r1(y1), "w": r1(x2 - x1), "h": r1(y2 - y1)})
        for j, b in enumerate(bars):
            x1, x2, by = geom[j]["x1"], geom[j]["x2"], geom[j]["by"]
            right = x_of(b["v"]) >= xb
            text = v_text(b["v"])
            out = {"x": x2 + 6, "y": c.mid(by + bar_h / 2), "anchor": "start"} if right else {"x": x1 - 6, "y": c.mid(by + bar_h / 2), "anchor": "end"}
            alt = {"x": x1 - 6, "y": out["y"], "anchor": "end"} if right else {"x": x2 + 6, "y": out["y"], "anchor": "start"}
            tone_pick = "text" if b["tone"] == "muted" else b["tone"]
            if not c.place(text, [out, alt], tone_pick, {"bold": True, "of": key}):
                fail("tornado", f'the value "{text}" of "{it["label"]}" has no room')
        y += row_h[k]

    xb = r1(x_of(s["base"]))
    c.line(xb, y0 - 6, xb, body_b, {"stroke": "text", "sw": 2})
    base_text = f"{s['baseLabel']} {v_text(s['base'])}"
    half = c.tw(base_text, True) / 2
    if 2 * half > g["w"]:
        fail("tornado", f'the base label "{base_text}" is wider than the figure (shorten baseLabel, or raise width)')
    c.text(base_text, min(max(xb, g["x"] + half), g["x"] + g["w"] - half), y0 - 12, "middle", "text", {"bold": True})

    return c.done()


def tornado_band(items: list[dict], opts: dict | None = None) -> dict:
    """lib/charts-dsl.ts's tornadoBand() + lib/dsl/charts.ts's tornado()."""
    opts = opts or {}
    spec = resolve_tornado(items, opts)
    alt = opts.get("alt") if opts.get("alt") is not None else tornado_alt(spec)
    band: dict = {"type": "chart", "kind": "tornado", "spec": spec, "alt": alt, "ids": [i["id"] for i in spec["items"] if i.get("id")]}
    band.update(common_chart_opts("tornado", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
    return band
