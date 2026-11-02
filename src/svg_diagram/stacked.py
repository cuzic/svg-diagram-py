"""1:1 port of lib/charts-stacked.ts's layoutStacked() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the stackedBars()/mekko() DSL constructors
(lib/charts-dsl.ts's stackedBand()) — defaults + the structural validations that affect
layout.

stackedTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
heatmapTexts()/sankeyTexts()/radarTexts()/treemapTexts()/waterfallTexts().

Golden master: lib/charts-stacked.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import json
import math

from .charts_base import Canvas, check_domain, check_ids, check_text, common_chart_opts, fail, finite_num, ink_on_shade, num_text, shade_ops, value_scale
from .charts_base import _to_precision as to_precision
from .emit_common import js_round


def resolve_stacked(who: str, columns: list[dict], mode: str, opts: dict) -> dict:
    """lib/charts-stacked.ts:23-54 resolveStacked()."""
    if not isinstance(columns, list) or len(columns) == 0:
        fail(who, "needs at least one column")
    limit = 12 if mode == "mekko" else 20
    if len(columns) > limit:
        fail(who, f"{len(columns)} columns are too many for one figure (at most {limit})")
    check_ids(who, [c.get("id") for c in columns], opts.get("id"))
    series: list[str] = []
    for k, col in enumerate(columns):
        check_text(who, f"column {k + 1}'s label", col["label"])
        if not isinstance(col.get("parts"), list) or len(col["parts"]) == 0:
            fail(who, f'column "{col["label"]}" needs parts: [{{label, value}}, ...]')
        seen: set[str] = set()
        for p in col["parts"]:
            check_text(who, f'a part of "{col["label"]}": label', p["label"])
            finite_num(who, f'"{p["label"]}" of "{col["label"]}"', p["value"], min=0)
            if p["label"] in seen:
                fail(who, f'column "{col["label"]}" has "{p["label"]}" twice')
            seen.add(p["label"])
            if p["label"] not in series:
                series.append(p["label"])
    if len(series) > 6:
        fail(who, f'{len(series)} different parts are too many to tell apart (at most 6: fold the small ones into "その他")')
    cols = []
    for c in columns:
        values = [next((p["value"] for p in c["parts"] if p["label"] == s), 0) for s in series]
        total = to_precision(sum(values), 12)
        if mode != "stacked" and not (total > 0):
            fail(who, f'column "{c["label"]}" adds up to 0, so it has no shares')
        col: dict = {"label": c["label"], "values": values, "total": total}
        if c.get("id") is not None:
            col["id"] = c["id"]
        cols.append(col)
    if mode == "stacked" and all(c["total"] == 0 for c in cols):
        fail(who, "every column is 0")
    if opts.get("axisGroup") is not None and opts["axisGroup"] is not False:
        fail(who, f"axisGroup must be false (this chart's axis is its own) or left out (got {json.dumps(opts['axisGroup'])})")
    domain = check_domain(who, opts.get("domain"))
    if domain and mode != "stacked":
        fail(who, "domain is for stacked columns (percent and mekko have no value axis to share)")
    spec: dict = {"mode": mode, "series": series, "columns": cols, "unit": opts.get("unit") or ""}
    if domain:
        spec["domain"] = domain
    if opts.get("axisGroup") is False:
        spec["axisGroup"] = False
    stacked_scale(spec)
    return spec


def _pct(v: float, total: float) -> str:
    return f"{num_text(js_round(v / total * 1000) / 10)}%"


def stacked_scale(s: dict) -> dict | None:
    """lib/charts-stacked.ts:56-58 stackedScale()."""
    if s["mode"] != "stacked":
        return None
    return value_scale("stackedBars", 0, max(c["total"] for c in s["columns"]), s.get("domain"))


def _seg_text(s: dict, v: float, total: float) -> str:
    if s["mode"] == "stacked":
        return f"{num_text(v)}{s['unit']}"
    return _pct(v, total)


def stacked_alt(s: dict) -> str:
    """lib/charts-stacked.ts:60-64 stackedAlt()."""
    name = "マリメッコ図" if s["mode"] == "mekko" else ("100%積み上げ棒グラフ" if s["mode"] == "percent" else "積み上げ棒グラフ")
    body = []
    for c in s["columns"]:
        parts = []
        for i, n in enumerate(s["series"]):
            v = c["values"][i]
            if v > 0 or s["mode"] == "stacked":
                suffix = "" if s["mode"] == "stacked" else f"（{_pct(v, c['total'])}）"
                parts.append(f"{n} {num_text(v)}{s['unit']}{suffix}")
        body.append(f"{c['label']}（計 {num_text(c['total'])}{s['unit']}）: {'、'.join(parts)}")
    return f"{name}: {'。'.join(body)}"


def layout_stacked(s: dict, g: dict) -> dict:
    """lib/charts-stacked.ts:79-174 layoutStacked()."""
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    lh = c.line_h()
    n = len(s["columns"])
    scale = stacked_scale(s)

    def r1(v: float) -> float:
        return js_round(v * 10) / 10

    if scale:
        ticks = [{"v": t, "f": t / scale["max"], "s": num_text(t)} for t in scale["ticks"]]
    else:
        ticks = [{"v": t, "f": t / 100, "s": f"{t}%"} for t in (0, 20, 40, 60, 80, 100)]
    tick_w = max(c.tw(t["s"]) for t in ticks)
    plot_l = g["x"] + tick_w + 16
    plot_r = g["x"] + g["w"] - 8
    gap = 3 if s["mode"] == "mekko" else 14

    ops = shade_ops(len(s["series"]))

    def op_of(i: int) -> float:
        return ops[len(s["series"]) - 1 - i]

    legend = []
    lx, ly = plot_l, 0.0
    for i, nm in enumerate(s["series"]):
        w = 14 + 6 + c.tw(nm) + 22
        if lx + w - 22 > plot_r and lx > plot_l:
            lx = plot_l
            ly += lh + 4
        legend.append({"x": lx, "y": ly, "i": i})
        lx += w
    legend_h = ly + size + 12

    total = sum(c2["total"] for c2 in s["columns"])
    avail = plot_r - plot_l - gap * (n - 1) - (0 if s["mode"] == "mekko" else gap)
    slot_w0 = (plot_r - plot_l) / n
    num_w = max([0.0] + [c.tw(_seg_text(s, v, k["total"]), True) + 8 for k in s["columns"] for v in k["values"] if v > 0])
    who = "mekko" if s["mode"] == "mekko" else "stackedBars"
    if s["mode"] == "stacked":
        tot_w = max(c.tw(f"{num_text(k['total'])}{s['unit']}", True) for k in s["columns"])
        if tot_w + 6 > slot_w0:
            fail(who, f"the column totals (up to {math.ceil(tot_w)}px) do not fit side by side in columns {math.floor(slot_w0)}px apart (raise width, use fewer columns, or a larger unit)")
    bar_w = min(max(min(96, slot_w0 * 0.6), num_w), slot_w0 - 12)
    widths = [avail * k["total"] / total if s["mode"] == "mekko" else max(bar_w, min(96, slot_w0 * 0.6)) for k in s["columns"]]
    if any(w < 1 for w in widths):
        fail(who, "a column is less than 1px wide (raise width, drop the smallest columns, or fold them together)")
    xs: list[float] = []
    if s["mode"] == "mekko":
        x = plot_l
        for w in widths:
            xs.append(x)
            x += w + gap
    else:
        slot = (plot_r - plot_l) / n
        for i, w in enumerate(widths):
            xs.append(plot_l + (i + 0.5) * slot - w / 2)

    cat_lines: list[dict] = []
    prev_right = [-math.inf, -math.inf, -math.inf]
    for i, k in enumerate(s["columns"]):
        if s["mode"] == "stacked":
            second: list[str] = []
        elif s["mode"] == "mekko":
            second = [f"計 {num_text(k['total'])}{s['unit']}", f"（{_pct(k['total'], total)}）"]
        else:
            second = [f"計 {num_text(k['total'])}{s['unit']}"]
        natural = max([c.tw(k["label"], True)] + [c.tw(t) for t in second])
        slot_w = (plot_r - plot_l) / n - 8
        tries = [max(widths[i], min(natural, 128)), max(widths[i] + 24, 60), max(widths[i], 40), 72] if s["mode"] == "mekko" else [slot_w]
        best = None
        for row in range(3):
            if best:
                break
            for max_w in tries:
                main = c.wrap(k["label"], max_w, True)
                sec = [l for t in second for l in c.wrap(t, max_w)]
                half = max([0.0] + [c.tw(l, True) for l in main] + [c.tw(l) for l in sec]) / 2
                cx = min(max(xs[i] + widths[i] / 2, g["x"] + half + 1), g["x"] + g["w"] - half - 1)
                if cx - half >= prev_right[row] + 6:
                    best = {"main": main, "second": sec, "cx": cx, "row": row}
                    prev_right[row] = cx + half
                    break
        if best is None:
            fail(who, f'the label of "{k["label"]}" has no room under its column (shorten the labels, or raise width)')
        cat_lines.append(best)

    block_h = max(len(k["main"]) + len(k["second"]) for k in cat_lines) * lh + 4
    cat_h = (max(k["row"] for k in cat_lines) + 1) * block_h + 13
    c.h = g["height"] if g.get("height") is not None else 340 + max(0, legend_h - 22) + cat_h - 30
    plot_t = g["y"] + legend_h + 8 + (size + 8 if s["mode"] == "stacked" else 4)
    plot_b = g["y"] + c.h - cat_h - 6
    if plot_b - plot_t < 120:
        fail(who, "the figure is too short; raise height")

    def y_of(f: float) -> float:
        return plot_b - f * (plot_b - plot_t)

    for l in legend:
        cy = g["y"] + l["y"] + max(9, math.ceil(size * 0.64))
        c.rect(l["x"], cy - 7, 14, 14, {"fill": "accent", "op": op_of(l["i"]), "stroke": "accent", "sw": 2})
        c.text(s["series"][l["i"]], l["x"] + 20, c.mid(cy), "start", "text")

    for t in ticks:
        c.line(plot_l - 6, y_of(t["f"]), plot_r, y_of(t["f"]), {"stroke": "text" if t["v"] == 0 else "border"})
        c.text(t["s"], plot_l - 10, c.mid(y_of(t["f"])), "end", "muted")
    c.line(plot_l, r1(y_of(1)), plot_l, r1(y_of(0)), {"stroke": "border"})

    omitted = c.omitted
    beside = []
    for ci, k in enumerate(s["columns"]):
        acc = 0.0
        top = k["total"]
        for si, nm in enumerate(s["series"]):
            v = k["values"][si]
            if not (v > 0):
                continue
            f0 = acc / scale["max"] if s["mode"] == "stacked" else acc / top
            f1 = (acc + v) / scale["max"] if s["mode"] == "stacked" else (acc + v) / top
            acc += v
            y1, y0 = y_of(f1), y_of(f0)
            full = y0 - y1
            gp = min(2, full * 0.3)
            h = full - gp
            op = op_of(si)
            ink = ink_on_shade(op)
            if h < 0.5:
                omitted.append(f"{nm} {_seg_text(s, v, k['total'])}（{k['label']}）")
                continue
            key = k.get("id") or f"#{ci}"
            host = c.rect(r1(xs[ci]), r1(y1 + gp), r1(widths[ci]), r1(h), {"fill": "accent", "op": op, "solid": f'"{nm}" in "{k["label"]}"', "of": key})
            whole = f"{nm} {_seg_text(s, v, k['total'])}"
            short = _seg_text(s, v, k["total"])
            room = h >= size + 6
            cx = xs[ci] + widths[ci] / 2
            cy = y1 + gp + h / 2
            if room and c.tw(whole, True) <= widths[ci] - 8:
                pick = whole
            elif room and c.tw(short, True) <= widths[ci] - 6:
                pick = short
            else:
                pick = None
            if pick:
                c.text(pick, cx, c.mid(cy), "middle", ink, {"bold": True, "host": host, "on": {"fill": "accent", "op": op, "ink": ink}, "of": key})
            elif s["mode"] == "mekko":
                omitted.append(f"{nm} {short}（{k['label']}）")
            else:
                beside.append({"text": whole, "x": xs[ci] + widths[ci] + 8, "y": c.mid(cy), "key": key, "left": f"{nm} {short}（{k['label']}）"})
        if k.get("id"):
            yv = k["total"] / scale["max"] if s["mode"] == "stacked" else 1
            c.anchors.append({"id": k["id"], "x": xs[ci], "y": y_of(yv), "w": widths[ci], "h": y_of(0) - y_of(yv)})
        if s["mode"] == "stacked":
            c.text(f"{num_text(k['total'])}{s['unit']}", xs[ci] + widths[ci] / 2, y_of(k["total"] / scale["max"]) - 7, "middle", "text", {"bold": True, "of": k.get("id") or f"#{ci}"})

    for b in beside:
        if not c.place(b["text"], [{"x": b["x"], "y": b["y"], "anchor": "start"}], "text", {"bold": True, "of": b["key"]}):
            omitted.append(b["left"])

    for ci, k in enumerate(s["columns"]):
        m = cat_lines[ci]
        cx = m["cx"]
        top = plot_b + size + 11 + m["row"] * block_h
        key = k.get("id") or f"#{ci}"
        c.lines(m["main"], cx, top, "middle", "text", {"bold": True, "of": key})
        c.lines(m["second"], cx, top + len(m["main"]) * lh, "middle", "muted", {"of": key})

    return c.done()


def stacked_band(who: str, columns: list[dict], mode: str, opts: dict) -> dict:
    """lib/charts-dsl.ts:66-69 stackedBand()."""
    spec = resolve_stacked(who, columns, mode, opts)
    alt = opts.get("alt") if opts.get("alt") is not None else stacked_alt(spec)
    band: dict = {"type": "chart", "kind": "stacked", "spec": spec, "alt": alt, "ids": [c["id"] for c in columns if c.get("id")]}
    band.update(common_chart_opts(who, id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
    return band


def stacked_bars_band(columns: list[dict], opts: dict | None = None) -> dict:
    """lib/dsl/charts.ts's stackedBars()."""
    opts = opts or {}
    return stacked_band("stackedBars", columns, "percent" if opts.get("percent") else "stacked", opts)


def mekko_band(columns: list[dict], opts: dict | None = None) -> dict:
    """lib/dsl/charts.ts's mekko()."""
    opts = opts or {}
    return stacked_band("mekko", columns, "mekko", opts)
