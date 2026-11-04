"""1:1 port of lib/charts-combo.ts's layoutCombo() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the combo() DSL constructor (lib/charts-dsl.ts's
comboBand()) — defaults + the structural validations that affect layout.

comboTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
the other chart kinds' *Texts() helpers.

Golden master: lib/charts-combo.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .charts_base import Canvas, ChartBand, check_ids, check_text, common_chart_opts, fail, finite_num, nice_scale, num_text, thin_ticks
from .emit_common import js_num, js_round, round1

BAR_TONES = ("accent", "text", "muted")
LINE_TONES = ("danger", "text", "accent")


def resolve_combo(categories: list[str], series: list[dict], opts: dict | None = None) -> dict:
    """lib/charts-combo.ts:31-74 resolveCombo()."""
    opts = opts or {}
    if not isinstance(categories, list) or len(categories) < 2:
        fail("combo", "needs at least two categories")
    if len(categories) > 24:
        fail("combo", f"{len(categories)} categories are too many for one figure (at most 24)")
    for i, k in enumerate(categories):
        check_text("combo", f"category {i + 1}", k)
    if not isinstance(series, list) or len(series) == 0:
        fail("combo", "needs at least one series")
    if len(set(categories)) != len(categories):
        fail("combo", "each category needs its own name")
    bars_in = [s for s in series if s["type"] == "bar"]
    lines_in = [s for s in series if s["type"] == "line"]
    if len(bars_in) + len(lines_in) != len(series):
        fail("combo", "each series' type must be 'bar' or 'line'")
    if len(bars_in) > 3:
        fail("combo", f"{len(bars_in)} bar series are too many to tell apart (at most 3)")
    if len(lines_in) > 3:
        fail("combo", f"{len(lines_in)} line series are too many to tell apart (at most 3)")
    check_ids("combo", [s.get("id") for s in series], opts.get("id"))
    labels = [check_text("combo", f"series {i + 1}'s label", s["label"]) for i, s in enumerate(series)]
    if len(set(labels)) != len(labels):
        fail("combo", "each series needs its own label")
    tones = ("accent", "danger", "muted", "text")
    b_idx = 0
    l_idx = 0
    out = []
    for s in series:
        if not isinstance(s.get("values"), list) or len(s["values"]) != len(categories):
            fail("combo", f'"{s["label"]}" needs {len(categories)} values, one per category (got {len(s["values"]) if isinstance(s.get("values"), list) else "none"}; null is a gap)')
        if s.get("tone") is not None and s["tone"] not in tones:
            fail("combo", f'"{s["label"]}" tone must be accent, danger, muted or text')
        if s.get("axis") is not None and s["axis"] not in ("left", "right"):
            fail("combo", f'"{s["label"]}" axis must be left or right')
        if s["type"] == "bar" and s.get("axis") == "right":
            fail("combo", f'"{s["label"]}": a bar is always on the left axis (put the line on the right)')
        values = [None if v is None else finite_num("combo", f'"{s["label"]}" value {i + 1}', v) for i, v in enumerate(s["values"])]
        if all(v is None for v in values):
            fail("combo", f'"{s["label"]}" has no value')
        if s.get("tone") is not None:
            tone = s["tone"]
        elif s["type"] == "bar":
            tone = BAR_TONES[b_idx]
            b_idx += 1
        else:
            tone = LINE_TONES[l_idx]
            l_idx += 1
        axis = "left" if s["type"] == "bar" else (s.get("axis") or ("right" if bars_in else "left"))
        item: dict = {"label": s["label"], "type": s["type"], "axis": axis, "values": values, "tone": tone}
        if s.get("id") is not None:
            item["id"] = s["id"]
        out.append(item)
    for a in ("y", "y2"):
        ax = opts.get(a) or {}
        for f in ("min", "max"):
            if ax.get(f) is not None:
                finite_num("combo", f"{a}.{f}", ax[f])
        if ax.get("min") is not None and ax.get("max") is not None and not (ax["max"] > ax["min"]):
            fail("combo", f"{a}.max must be larger than {a}.min")
    if not any(s["axis"] == "left" for s in out):
        fail("combo", "needs a bar or a line on the left axis (the left axis is the one the figure is read from)")
    for a in ("left", "right"):
        ax = (opts.get("y") if a == "left" else opts.get("y2")) or {}
        mine = [s for s in out if s["axis"] == a]
        v = [x for s in mine for x in s["values"] if x is not None]
        top = [sum((s["values"][i] or 0) for s in mine if s["type"] == "bar") for i in range(len(categories))] if (opts.get("stack") and a == "left") else []
        has_bar = a == "left" and any(s["type"] == "bar" for s in mine)
        name = "y" if a == "left" else "y2"
        if ax.get("max") is not None:
            mx = max(v + top + ([0] if has_bar else []))
            if mx > ax["max"]:
                fail("combo", f"{name}.max {ax['max']} is below the data ({mx}): raise it, or leave it out")
        if ax.get("min") is not None:
            mn = min(v + ([0] if has_bar else []))
            if mn < ax["min"]:
                reason = "zero, where bars start" if (has_bar and ax["min"] > 0) else f"the data ({min(v)})"
                fail("combo", f"{name}.min {ax['min']} is above {reason}: lower it, or leave it out")
    if opts.get("stack") and len(bars_in) < 2:
        fail("combo", "stack needs at least two bar series")
    if opts.get("stack"):
        for s in out:
            if s["type"] == "bar" and any(v is not None and v < 0 for v in s["values"]):
                fail("combo", f'"{s["label"]}": stacked bars cannot be negative')
    if not any(s["axis"] == "right" for s in out) and opts.get("y2") is not None:
        fail("combo", "y2 is given but no series reads on the right axis")
    return {"categories": list(categories), "series": out, "y": opts.get("y") or {}, "y2": opts.get("y2") or {}, "values": opts.get("values") is not False, "stack": opts.get("stack") is True}


def _unit_of(s: dict, axis: str) -> str:
    return (s["y"] if axis == "left" else s["y2"]).get("unit") or ""


def _vals(s: dict, axis: str) -> list[float]:
    return [v for x in s["series"] if x["axis"] == axis for v in x["values"] if v is not None]


def combo_alt(s: dict) -> str:
    """lib/charts-combo.ts:77-79 comboAlt()."""
    parts = []
    for x in s["series"]:
        kind = "棒" if x["type"] == "bar" else "折れ線"
        vals = "、".join(f"{k} {'なし' if x['values'][i] is None else num_text(x['values'][i]) + _unit_of(s, x['axis'])}" for i, k in enumerate(s["categories"]))
        parts.append(f"{kind} {x['label']}（{vals}）")
    return f"コンボチャート: {'、'.join(parts)}"


def _totals(s: dict) -> list[float]:
    """lib/charts-combo.ts:81 totals()."""
    return [sum((x["values"][i] or 0) for x in s["series"] if x["type"] == "bar") for i in range(len(s["categories"]))]


def _scale_of(s: dict, axis: str, want: int = 5) -> dict:
    """lib/charts-combo.ts:83-88 scaleOf()."""
    ax = s["y"] if axis == "left" else s["y2"]
    v = _vals(s, axis)
    has_bar = axis == "left" and any(x["type"] == "bar" for x in s["series"])
    top = _totals(s) if (s["stack"] and has_bar) else []
    ax_min, ax_max = ax.get("min"), ax.get("max")
    lo = ax_min if ax_min is not None else min(v + ([0] if has_bar else []))
    hi = ax_max if ax_max is not None else max(v + top + ([0] if has_bar else []))
    return nice_scale(lo, hi, want)


def layout_combo(s: dict, g: dict) -> dict:
    """lib/charts-combo.ts:106-220 layoutCombo()."""
    size = g["size"]
    n = len(s["categories"])
    c = Canvas(g["x"], g["y"], g["w"], g["height"] if g.get("height") is not None else 380, size, g["widthOf"], g["wrap"])

    r1 = round1

    has_right = any(x["axis"] == "right" for x in s["series"])
    sl = _scale_of(s, "left")
    intervals = len(sl["ticks"]) - 1
    sr = _scale_of(s, "right") if has_right else None
    aligned = False
    if has_right:
        for w in (intervals, intervals - 1, intervals + 1, intervals - 2, intervals + 2, 2, 3, 4, 5, 6, 7, 8):
            t = _scale_of(s, "right", max(1, w))
            if len(t["ticks"]) - 1 == intervals:
                sr = t
                aligned = True
                break
    lw = max(c.tw(num_text(t)) for t in sl["ticks"])
    rw = max(c.tw(num_text(t)) for t in sr["ticks"]) if sr else 0
    plot_l = g["x"] + lw + 14
    plot_r = g["x"] + g["w"] - (rw + 14 if has_right else 8)
    slot = (plot_r - plot_l) / n
    if slot < size * 2.2:
        fail("combo", f"{n} categories do not fit in {js_round(g['w'])}px (raise width, or use fewer categories)")
    bars = [x for x in s["series"] if x["type"] == "bar"]
    lines = [x for x in s["series"] if x["type"] == "line"]
    nb = 1 if s["stack"] else len(bars)
    group_w = min(slot * 0.7, (72 if s["stack"] else 56 * len(bars)))
    bw = (math.floor(group_w / nb) - (2 if nb > 1 else 0)) if nb else 0
    cats = [c.wrap(k, slot - 6) for k in s["categories"]]
    cat_h = max(len(l) for l in cats) * c.line_h() + math.ceil(size * 0.36) + 6
    for i, ls in enumerate(cats):
        for l in ls:
            if c.tw(l) > slot - 2:
                fail("combo", f'the category "{s["categories"][i]}" is too long for a column {js_round(slot)}px wide (shorten it, or raise width)')
    sw = 14

    def item_w(x: dict) -> float:
        return (sw if x["type"] == "bar" else sw + 10) + 6 + c.tw(x["label"])

    legend = []
    lx = plot_l
    row = 0
    for x in s["series"]:
        if item_w(x) > g["w"]:
            fail("combo", f'the series name "{x["label"]}" is wider than the figure (shorten it, or raise width)')
        if lx > plot_l and lx + item_w(x) > g["x"] + g["w"]:
            lx = plot_l
            row += 1
        legend.append({"x": lx, "row": row, "s": x})
        lx += item_w(x) + 22
    legend_rows = legend[-1]["row"] + 1
    row_pitch = size + 12

    def ax_title(ax: dict) -> str:
        return ax.get("title") or ax.get("unit") or ""

    title_h = size + 10 if (ax_title(s["y"]) or (has_right and ax_title(s["y2"]))) else 0
    head_h = legend_rows * row_pitch + title_h + 4
    plot_t = g["y"] + head_h
    plot_b = g["y"] + c.h - cat_h - 6
    y_top = plot_t + math.ceil(size / 2) + 4
    y_bot = plot_b
    if y_bot - y_top < 100:
        fail("combo", "the figure is too short for its labels; raise height")

    def y_l(v: float) -> float:
        return y_bot - (v - sl["min"]) / (sl["max"] - sl["min"]) * (y_bot - y_top)

    def y_r(v: float) -> float:
        assert sr is not None  # only called via y_of() for a "right"-axis series, which implies has_right
        return y_bot - (v - sr["min"]) / (sr["max"] - sr["min"]) * (y_bot - y_top)

    def y_of(x: dict):
        return y_l if x["axis"] == "left" else y_r

    def text_of(x: dict, v: float) -> str:
        return f"{num_text(v)}{_unit_of(s, x['axis'])}"

    shapes = ("disc", "square", "diamond")

    def mark(kind: str, cx: float, cy: float, r: float, tone: str, of: str) -> None:
        if kind == "disc":
            d = f"M{js_num(r1(cx - r))},{js_num(r1(cy))} a{js_num(r)},{js_num(r)} 0 1,0 {js_num(2 * r)},0 a{js_num(r)},{js_num(r)} 0 1,0 {js_num(-2 * r)},0 Z"
        elif kind == "square":
            d = f"M{js_num(r1(cx - r))},{js_num(r1(cy - r))} h{js_num(2 * r)} v{js_num(2 * r)} h{js_num(-2 * r)} Z"
        else:
            d = f"M{js_num(r1(cx))},{js_num(r1(cy - r - 1))} l{js_num(r + 1)},{js_num(r + 1)} l{js_num(-r - 1)},{js_num(r + 1)} l{js_num(-r - 1)},{js_num(-r - 1)} Z"
        c.path(d, {"fill": tone, "stroke": "bg", "sw": 1, "of": of})
        c.marks.append({"x": cx - r - 1, "y": cy - r - 1, "w": 2 * r + 2, "h": 2 * r + 2})

    for L in legend:
        cy = g["y"] + L["row"] * row_pitch + max(4 + sw / 2, math.ceil(size * 0.64))
        key = L["s"].get("id") or L["s"]["label"]
        if L["s"]["type"] == "bar":
            c.rect(L["x"], cy - sw / 2, sw, sw, {"fill": L["s"]["tone"], "op": 0.4, "stroke": L["s"]["tone"], "sw": 1})
        else:
            li = next(i for i, x in enumerate(lines) if x is L["s"])
            c.line(L["x"], cy, L["x"] + sw + 10, cy, {"stroke": L["s"]["tone"], "sw": 3, "dash": "6,4" if li == 1 else None})
            mark(shapes[li], L["x"] + (sw + 10) / 2, cy, 4, L["s"]["tone"], key)
        c.text(L["s"]["label"], L["x"] + (sw if L["s"]["type"] == "bar" else sw + 10) + 6, c.mid(cy), "start", "text")
    c.marks.clear()

    tk = [{"v": v} for v in sl["ticks"]]
    shown = thin_ticks(tk, y_l, lambda t: size + 2, 2)
    for t in tk:
        y = r1(y_l(t["v"]))
        c.line(plot_l - 6, y, plot_r + (6 if has_right else 0), y, {"stroke": "text" if t["v"] == 0 else "border"})
        if t in shown:
            c.text(num_text(t["v"]), plot_l - 10, c.mid(y), "end", "muted")
    if sr:
        rt = [{"v": v} for v in sr["ticks"]]
        r_shown = thin_ticks(rt, y_r, lambda t: size + 2, 2)
        for t in rt:
            y = r1(y_r(t["v"]))
            if not aligned:
                c.line(plot_r, y, plot_r + 6, y, {"stroke": "border"})
            if t in r_shown:
                c.text(num_text(t["v"]), plot_r + 10, c.mid(y), "start", "muted")
    if ax_title(s["y"]):
        c.text(ax_title(s["y"]), g["x"], plot_t - 6, "start", "text", {"bold": True})
    if has_right and ax_title(s["y2"]):
        c.text(ax_title(s["y2"]), g["x"] + g["w"], plot_t - 6, "end", "text", {"bold": True})

    stacked_below = [0.0] * n
    bar_geo: list[list[dict | None]] = []
    for bi, x in enumerate(bars):
        row_geo: list[dict | None] = []
        for i, v in enumerate(x["values"]):
            if v is None:
                row_geo.append(None)
                continue
            cx = plot_l + (i + 0.5) * slot
            if s["stack"]:
                x0 = cx - bw / 2
            else:
                x0 = cx - group_w / 2 + bi * (bw + (2 if nb > 1 else 0)) + (group_w - nb * bw - (nb - 1) * (2 if nb > 1 else 0)) / 2
            base = stacked_below[i] if s["stack"] else 0
            if s["stack"]:
                stacked_below[i] = base + v
            a = y_l(max(v, 0) + base)
            b = y_l(min(v, 0) + base)
            top = a - 1 if b - a < 2 else a
            h = max(2, b - a)
            key = x.get("id") or x["label"]
            c.rect(r1(x0), r1(top), bw, r1(h), {"fill": x["tone"], "op": 0.4, "stroke": x["tone"], "sw": 1, "of": key})
            row_geo.append({"x": x, "v": v, "cx": x0 + bw / 2, "top": top, "h": h, "key": key})
        bar_geo.append(row_geo)

    line_geo = []
    for li, x in enumerate(lines):
        pts: list[dict | None] = []
        for i, v in enumerate(x["values"]):
            pts.append(None if v is None else {"x": plot_l + (i + 0.5) * slot, "y": y_of(x)(v), "v": v, "i": i})
        key = x.get("id") or x["label"]
        d_parts = []
        pen = False
        for p in pts:
            if p is None:
                pen = False
                continue
            cmd = "L" if pen else "M"
            d_parts.append(f"{cmd}{js_num(r1(p['x']))},{js_num(r1(p['y']))} ")
            pen = True
        c.path("".join(d_parts).strip(), {"fill": "none", "stroke": x["tone"], "sw": 3, "dash": "6,4" if li == 1 else None, "of": key})
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if a and b:
                c.segs.append({"x1": a["x"], "y1": a["y"], "x2": b["x"], "y2": b["y"]})
        for p in pts:
            if p:
                mark(shapes[li], p["x"], p["y"], 4, x["tone"], key)
        line_geo.append({"x": x, "pts": pts, "key": key})

    for bi, x in enumerate(bars):
        if x.get("id"):
            g2 = [q for q in bar_geo[bi] if q]
            x1 = min(q["cx"] - bw / 2 for q in g2)
            x2 = max(q["cx"] + bw / 2 for q in g2)
            y1 = min(q["top"] for q in g2)
            y2 = max(q["top"] + q["h"] for q in g2)
            c.anchors.append({"id": x["id"], "x": r1(x1), "y": r1(y1), "w": r1(x2 - x1), "h": r1(y2 - y1)})
    for L in line_geo:
        if L["x"].get("id"):
            p = [q for q in L["pts"] if q]
            x1 = min(q["x"] for q in p) - 5
            x2 = max(q["x"] for q in p) + 5
            y1 = min(q["y"] for q in p) - 5
            y2 = max(q["y"] for q in p) + 5
            c.anchors.append({"id": L["x"]["id"], "x": r1(x1), "y": r1(y1), "w": r1(x2 - x1), "h": r1(y2 - y1)})

    def in_plot(b: dict) -> bool:
        return b["y"] >= plot_t - 2 and b["y"] + b["h"] <= plot_b + 1

    if s["values"]:
        for row_geo in bar_geo:
            for q in row_geo:
                if not q:
                    continue
                txt = text_of(q["x"], q["v"])
                up = q["v"] >= 0
                if s["stack"]:
                    fits = q["h"] >= size + 6 and c.tw(txt, True) <= bw - 4
                    if not fits or not c.place(txt, [{"x": q["cx"], "y": c.mid(q["top"] + q["h"] / 2), "anchor": "middle"}], "text", {"bold": True, "of": q["key"]}):
                        c.omitted.append(f"{q['x']['label']} {s['categories'][js_round((q['cx'] - plot_l) / slot - 0.5)]} {txt}")
                    continue
                above = {"x": q["cx"], "y": q["top"] - 6, "anchor": "middle"}
                below = {"x": q["cx"], "y": q["top"] + q["h"] + size + 4, "anchor": "middle"}
                inside = {"x": q["cx"], "y": c.mid(q["top"] + q["h"] / 2), "anchor": "middle"}

                def ok(cs: list[dict]) -> list[dict]:
                    return [k for k in cs if in_plot(c.box_of(txt, k["x"], k["y"], k["anchor"], True))]

                chosen = ok([above, below, inside]) if up else ok([below, above, inside])
                if not c.place(txt, chosen, "text", {"bold": True, "of": q["key"]}):
                    c.omitted.append(f"{q['x']['label']} {s['categories'][js_round((q['cx'] - plot_l) / slot - 0.5)]} {txt}")
        if s["stack"]:
            for i, v in enumerate(_totals(s)):
                txt = f"{num_text(v)}{_unit_of(s, 'left')}"
                top = y_l(v)
                cx = plot_l + (i + 0.5) * slot
                cs = [k for k in [{"x": cx, "y": top - 6, "anchor": "middle"}] if in_plot(c.box_of(txt, k["x"], k["y"], k["anchor"], True))]
                if not c.place(txt, cs, "text", {"bold": True}):
                    c.omitted.append(f"合計 {s['categories'][i]} {txt}")
        for L in line_geo:
            for p in L["pts"]:
                if not p:
                    continue
                txt = text_of(L["x"], p["v"])
                rr = 7
                cands = [
                    {"x": p["x"], "y": p["y"] - rr - 3, "anchor": "middle"},
                    {"x": p["x"], "y": p["y"] + rr + size + 1, "anchor": "middle"},
                    {"x": p["x"] + rr + 4, "y": c.mid(p["y"]), "anchor": "start"},
                    {"x": p["x"] - rr - 4, "y": c.mid(p["y"]), "anchor": "end"},
                    {"x": p["x"] + rr, "y": p["y"] - rr - 3, "anchor": "start"},
                    {"x": p["x"] - rr, "y": p["y"] - rr - 3, "anchor": "end"},
                ]
                filtered = [k for k in cands if in_plot(c.box_of(txt, k["x"], k["y"], k["anchor"], True))]
                tone_pick = "text" if L["x"]["tone"] == "muted" else L["x"]["tone"]
                if not c.place(txt, filtered, tone_pick, {"bold": True, "of": L["key"]}):
                    c.omitted.append(f"{L['x']['label']} {s['categories'][p['i']]} {txt}")

    for i, ls in enumerate(cats):
        c.lines(ls, plot_l + (i + 0.5) * slot, plot_b + math.ceil(size * 0.36) + size + 8, "middle", "text")

    return c.done()


def combo_band(categories: list[str], series: list[dict], opts: dict | None = None) -> ChartBand:
    """lib/charts-dsl.ts:126-129 comboBand() + lib/dsl/charts.ts's combo()."""
    opts = opts or {}
    spec = resolve_combo(categories, series, opts)
    opt_alt = opts.get("alt")
    alt = opt_alt if opt_alt is not None else combo_alt(spec)
    return ChartBand(kind="combo", spec=spec, alt=alt, **common_chart_opts("combo", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
