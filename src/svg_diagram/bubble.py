"""1:1 port of lib/charts-bubble.ts's layoutBubble() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the bubble() DSL constructor (lib/charts-dsl.ts's
bubbleBand()) — defaults + the structural validations that affect layout.

bubbleTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
the other chart kinds' *Texts() helpers.

Golden master: lib/charts-bubble.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .charts_base import Canvas, check_ids, check_text, common_chart_opts, fail, finite_num, nice_scale, num_text, overlaps, thin_ticks
from .charts_base import _to_precision as to_precision
from .emit_common import js_num, js_round

MAX_WIDEN = 8


def resolve_bubble(points: list[dict], opts: dict | None = None) -> dict:
    """lib/charts-bubble.ts:27-43 resolveBubble()."""
    opts = opts or {}
    if not isinstance(points, list) or len(points) == 0:
        fail("bubble", "needs at least one point")
    if len(points) > 30:
        fail("bubble", f"{len(points)} bubbles are too many to name on one figure (at most 30)")
    check_ids("bubble", [p.get("id") for p in points], opts.get("id"))
    tones = ("accent", "danger", "muted", "text")
    lst = []
    for k, p in enumerate(points):
        if p.get("tone") is not None and p["tone"] not in tones:
            fail("bubble", f'"{p["label"]}" tone must be accent, danger, muted or text')
        item: dict = {
            "label": check_text("bubble", f"point {k + 1}'s label", p["label"]),
            "x": finite_num("bubble", f'"{p["label"]}" x', p["x"]),
            "y": finite_num("bubble", f'"{p["label"]}" y', p["y"]),
            "size": finite_num("bubble", f'"{p["label"]}" size', p["size"]),
        }
        if p.get("tone") is not None:
            item["tone"] = p["tone"]
        if p.get("id") is not None:
            item["id"] = p["id"]
        lst.append(item)
    for p in lst:
        if not (p["size"] > 0):
            fail("bubble", f'"{p["label"]}" size must be > 0 (got {p["size"]}): the area of a circle cannot stand for zero or a negative')
    if len({p["label"] for p in lst}) != len(lst):
        fail("bubble", "each point needs its own label")
    for k in ("x", "y"):
        a = opts.get(k) or {}
        for f in ("min", "max", "line"):
            if a.get(f) is not None:
                finite_num("bubble", f"{k}.{f}", a[f])
        if a.get("min") is not None and a.get("max") is not None and not (a["max"] > a["min"]):
            fail("bubble", f"{k}.max must be larger than {k}.min")
    return {"points": lst, "x": opts.get("x") or {}, "y": opts.get("y") or {}, "sizeTitle": opts.get("sizeTitle") or "", "sizeUnit": opts.get("sizeUnit") or ""}


def bubble_alt(s: dict) -> str:
    """lib/charts-bubble.ts:44-47 bubbleAlt()."""

    def u(a: dict) -> str:
        return a.get("unit") or ""

    x_title = s["x"].get("title") or ""
    y_title = s["y"].get("title") or ""
    parts = [f"{p['label']}（{num_text(p['x'])}{u(s['x'])}、{num_text(p['y'])}{u(s['y'])}、{num_text(p['size'])}{s['sizeUnit']}）" for p in s["points"]]
    return f"バブルチャート（横軸: {x_title}、縦軸: {y_title}、円の面積: {s['sizeTitle']}）: {'、'.join(parts)}"


def _axis_range(s: dict, k: str) -> dict:
    """lib/charts-bubble.ts:49-52 axisRange()."""
    a = s[k]
    vals = [p[k] for p in s["points"]]
    ref = [] if a.get("line") is None else [a["line"]]
    lo = a.get("min") if a.get("min") is not None else min(vals + ref)
    hi = a.get("max") if a.get("max") is not None else max(vals + ref)
    return {"lo": lo, "hi": hi}


def _legend_text(s: dict, ref: float) -> str:
    base = f"円の面積 = {s['sizeTitle']}" if s["sizeTitle"] else "円の面積"
    return f"{base}（円 = {num_text(ref)}{s['sizeUnit']}）"


def _widen(sc: dict, side: str) -> dict:
    """lib/charts-bubble.ts:71-74 widen()."""
    min_v = to_precision(sc["min"] - sc["step"], 12) if side == "lo" else sc["min"]
    max_v = to_precision(sc["max"] + sc["step"], 12) if side == "hi" else sc["max"]
    ticks = [min_v, *sc["ticks"]] if side == "lo" else [*sc["ticks"], max_v]
    return {"min": min_v, "max": max_v, "step": sc["step"], "ticks": ticks}


def round_below(v: float) -> float:
    """lib/charts-bubble.ts:77-80 roundBelow(): a round value (1, 2 or 5 x a power of ten) at most `v`."""
    e = 10 ** math.floor(math.log10(v))
    m = v / e
    mult = 5 if m >= 5 else (2 if m >= 2 else 1)
    return mult * e


def layout_bubble(s: dict, g: dict) -> dict:
    """lib/charts-bubble.ts:82-166 layoutBubble()."""
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], g["height"] if g.get("height") is not None else 440, size, g["widthOf"], g["wrap"])

    def r1(v: float) -> float:
        return js_round(v * 10) / 10

    xs = _axis_range(s, "x")
    ys = _axis_range(s, "y")
    sx = nice_scale(xs["lo"], xs["hi"])
    sy = nice_scale(ys["lo"], ys["hi"])

    def tick_text(k: str, v: float) -> str:
        return f"{num_text(v)}{s[k].get('unit') or ''}"

    def y_tick_w_of() -> float:
        return max(c.tw(tick_text("y", t)) for t in sy["ticks"])

    max_size = max(p["size"] for p in s["points"])
    x_tick = math.ceil(size * 0.36) + 6
    title_h = size + 10 if s["y"].get("title") else 0
    x_axis_h = x_tick + size + 6 + (size + 8 if s["x"].get("title") else 0)
    r_max = max(14, min(40, min(g["w"], c.h) / 12))
    legend_h = max(size + 14, 2 * r_max + 8)

    def x_tick_half() -> float:
        return math.ceil(max(c.tw(tick_text("x", v)) for v in sx["ticks"]) / 2) + 2

    plot_l = g["x"] + y_tick_w_of() + 16
    plot_r = g["x"] + g["w"] - max(12, x_tick_half())
    plot_t = g["y"] + max(title_h + 6, math.ceil(size * 0.64) + 2)
    plot_b = g["y"] + c.h - x_axis_h - legend_h - 4
    if plot_r - plot_l < 160 or plot_b - plot_t < 120:
        fail("bubble", "the figure is too small for its axes (raise width / height)")
    r_min = 6

    def radius(v: float) -> float:
        return max(r_min, r_max * math.sqrt(v / max_size))

    def x_of(v: float) -> float:
        return plot_l + (v - sx["min"]) / (sx["max"] - sx["min"]) * (plot_r - plot_l)

    def y_of(v: float) -> float:
        return plot_b - (v - sy["min"]) / (sy["max"] - sy["min"]) * (plot_b - plot_t)

    for _guard in range(3 * MAX_WIDEN):
        grew = False
        for p in s["points"]:
            r = radius(p["size"])
            if s["x"].get("min") is None and x_of(p["x"]) - r < plot_l - 1:
                sx = _widen(sx, "lo")
                grew = True
            if s["x"].get("max") is None and x_of(p["x"]) + r > plot_r + 1:
                sx = _widen(sx, "hi")
                grew = True
            if s["y"].get("min") is None and y_of(p["y"]) + r > plot_b + 1:
                sy = _widen(sy, "lo")
                grew = True
            if s["y"].get("max") is None and y_of(p["y"]) - r < plot_t - 1:
                sy = _widen(sy, "hi")
                grew = True
            if grew:
                plot_l = g["x"] + y_tick_w_of() + 16
                plot_r = g["x"] + g["w"] - max(12, x_tick_half())
                break
        if not grew:
            l = g["x"] + y_tick_w_of() + 16
            r = g["x"] + g["w"] - max(12, x_tick_half())
            if l == plot_l and r == plot_r:
                break
            plot_l, plot_r = l, r

    yt = [{"v": v} for v in sy["ticks"]]
    xt = [{"v": v} for v in sx["ticks"]]
    y_shown = thin_ticks(yt, y_of, lambda t: size + 2, 2)
    x_shown = thin_ticks(xt, x_of, lambda t: c.tw(tick_text("x", t["v"])), 12)
    for t in yt:
        c.line(plot_l, r1(y_of(t["v"])), plot_r, r1(y_of(t["v"])), {"stroke": "border"})
        if t in y_shown:
            c.text(tick_text("y", t["v"]), plot_l - 8, c.mid(y_of(t["v"])), "end", "muted")
    for t in xt:
        c.line(r1(x_of(t["v"])), plot_t, r1(x_of(t["v"])), plot_b, {"stroke": "border"})
        if t in x_shown:
            c.text(tick_text("x", t["v"]), r1(x_of(t["v"])), plot_b + x_tick + size, "middle", "muted")
    c.line(plot_l, plot_b, plot_r, plot_b, {"stroke": "text"})
    c.line(plot_l, plot_t, plot_l, plot_b, {"stroke": "text"})
    if s["y"].get("title"):
        c.text(s["y"]["title"], plot_l, g["y"] + size, "start", "text", {"bold": True})
    if s["x"].get("title"):
        c.text(s["x"]["title"], (plot_l + plot_r) / 2, plot_b + x_tick + 2 * size + 8, "middle", "text", {"bold": True})

    if s["x"].get("line") is not None and sx["min"] <= s["x"]["line"] <= sx["max"]:
        x = r1(x_of(s["x"]["line"]))
        c.line(x, plot_t, x, plot_b, {"stroke": "muted", "dash": "6,4", "sw": 2})
        if s["x"].get("lineLabel"):
            c.place(s["x"]["lineLabel"], [{"x": x + 5, "y": plot_t + size, "anchor": "start"}, {"x": x - 5, "y": plot_t + size, "anchor": "end"}], "muted", {"plate": True})
    if s["y"].get("line") is not None and sy["min"] <= s["y"]["line"] <= sy["max"]:
        yv = r1(y_of(s["y"]["line"]))
        c.line(plot_l, yv, plot_r, yv, {"stroke": "muted", "dash": "6,4", "sw": 2})
        if s["y"].get("lineLabel"):
            c.place(s["y"]["lineLabel"], [{"x": plot_r - 4, "y": yv - 5, "anchor": "end"}, {"x": plot_r - 4, "y": yv + size + 4, "anchor": "end"}], "muted", {"plate": True})

    bs = [{"p": p, "i": i, "cx": x_of(p["x"]), "cy": y_of(p["y"]), "r": radius(p["size"]), "tone": p.get("tone") or "accent", "key": p.get("id") or f"#{i}"} for i, p in enumerate(s["points"])]

    for b in sorted(bs, key=lambda b: (-b["r"], b["i"])):
        if b["cx"] - b["r"] < plot_l - 2 or b["cx"] + b["r"] > plot_r + 2 or b["cy"] - b["r"] < plot_t - 2 or b["cy"] + b["r"] > plot_b + 2:
            fail("bubble", f'the bubble "{b["p"]["label"]}" runs out of the plot (widen the axis: x / y min / max)')
        rr = r1(b["r"])
        d = f"M{js_num(r1(b['cx'] - rr))},{js_num(r1(b['cy']))} a{js_num(rr)},{js_num(rr)} 0 1,0 {js_num(r1(2 * rr))},0 a{js_num(rr)},{js_num(rr)} 0 1,0 {js_num(r1(-2 * rr))},0 Z"
        c.path(d, {"fill": b["tone"], "op": 0.3, "stroke": b["tone"], "sw": 2, "of": b["key"]})
        c.anchors.append({"id": b["p"].get("id") or f"#{b['i']}", "x": r1(b["cx"] - rr), "y": r1(b["cy"] - rr), "w": r1(2 * rr), "h": r1(2 * rr)})
    c.anchors[:] = [a for a in c.anchors if not a["id"].startswith("#")]
    for b in bs:
        c.marks.append({"x": b["cx"] - b["r"], "y": b["cy"] - b["r"], "w": 2 * b["r"], "h": 2 * b["r"]})

    def at(x: float, y: float, anchor: str) -> dict:
        return {"x": x, "y": y, "anchor": anchor}

    for b in sorted(bs, key=lambda b: (-b["r"], b["i"])):
        label = b["p"]["label"]
        w = c.tw(label, True)
        mine = c.marks[b["i"]]
        inside = c.box_of(label, js_round(b["cx"]), c.mid(b["cy"]), "middle", True)
        room_inside = w + 8 <= 2 * b["r"] * 0.82 and size + 6 <= 2 * b["r"] * 0.82
        if room_inside:
            others = [m for m in c.marks if m is not mine]
            if not any(overlaps(inside, o) for o in c.boxes) and not any(overlaps(inside, m) for m in others):
                c.text(label, b["cx"], c.mid(b["cy"]), "middle", "text", {"bold": True, "of": b["key"], "on": {"fill": b["tone"], "op": 0.3, "ink": "text"}})
                continue
        c.marks[b["i"]] = {"x": 0, "y": 0, "w": 0, "h": 0}
        gap = 6
        cands = [
            at(b["cx"] + b["r"] + gap, c.mid(b["cy"]), "start"),
            at(b["cx"] - b["r"] - gap, c.mid(b["cy"]), "end"),
            at(b["cx"], b["cy"] - b["r"] - gap, "middle"),
            at(b["cx"], b["cy"] + b["r"] + gap + size, "middle"),
            at(b["cx"] + b["r"] * 0.7 + gap, b["cy"] - b["r"] * 0.7 - gap, "start"),
            at(b["cx"] - b["r"] * 0.7 - gap, b["cy"] - b["r"] * 0.7 - gap, "end"),
            at(b["cx"] + b["r"] * 0.7 + gap, b["cy"] + b["r"] * 0.7 + gap + size, "start"),
            at(b["cx"] - b["r"] * 0.7 - gap, b["cy"] + b["r"] * 0.7 + gap + size, "end"),
        ]
        done = c.place(label, cands, "text", {"bold": True, "of": b["key"]})
        c.marks[b["i"]] = {"x": b["cx"] - b["r"], "y": b["cy"] - b["r"], "w": 2 * b["r"], "h": 2 * b["r"]}
        if not done:
            fail("bubble", f'the name "{label}" has no room beside its bubble (thin out the points, or raise width / height)')

    ref = round_below(max_size)
    rr = radius(ref)
    ltext = _legend_text(s, ref)
    if rr * 2 + 12 + c.tw(ltext) > g["w"]:
        fail("bubble", "the size legend does not fit (shorten sizeTitle / sizeUnit, or raise width)")
    lcy = g["y"] + c.h - legend_h / 2
    c.path(
        f"M{js_num(r1(plot_l + 2))},{js_num(r1(lcy))} a{js_num(r1(rr))},{js_num(r1(rr))} 0 1,0 {js_num(r1(2 * rr))},0 a{js_num(r1(rr))},{js_num(r1(rr))} 0 1,0 {js_num(r1(-2 * rr))},0 Z",
        {"fill": "text", "op": 0.15, "stroke": "text", "sw": 2},
    )
    c.text(ltext, plot_l + 2 * rr + 12, c.mid(lcy), "start", "text")
    return c.done()


def bubble_band(points: list[dict], opts: dict | None = None) -> dict:
    """lib/charts-dsl.ts:116-119 bubbleBand() + lib/dsl/charts.ts's bubble()."""
    opts = opts or {}
    spec = resolve_bubble(points, opts)
    alt = opts.get("alt") if opts.get("alt") is not None else bubble_alt(spec)
    band: dict = {"type": "chart", "kind": "bubble", "spec": spec, "alt": alt, "ids": [p["id"] for p in points if p.get("id")]}
    band.update(common_chart_opts("bubble", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
    return band
