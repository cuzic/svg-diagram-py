"""1:1 port of lib/charts-waterfall.ts's layoutWaterfall()/layoutWaterfallH() (exported,
golden-tested live via charts.layout_chart()'s dispatch) and the waterfall() DSL constructor
(lib/charts-dsl.ts's waterfallBand()) — defaults + the structural validations that affect
layout.

waterfallTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
heatmapTexts()/sankeyTexts()/radarTexts()/treemapTexts().

Golden master: lib/charts-waterfall.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import json
import math

from .charts_base import Canvas, ChartBand, check_domain, check_ids, check_inset, check_text, common_chart_opts, fail, finite_num, inset_or_need, num_text, signed_text, thin_ticks, value_scale
from .charts_base import _to_precision as to_precision
from .emit_common import js_round, round1

KINDS = ("start", "delta", "subtotal", "total")
KIND_JA: dict[str, str] = {"start": "開始", "delta": "増減", "subtotal": "小計", "total": "合計"}
FILL: dict[str, str] = {"start": "text", "delta": "accent", "subtotal": "muted", "total": "text"}


def _mk_step(label: str, kind: str, value: float, from_: float, to: float, s: dict) -> dict:
    step: dict = {"label": label, "kind": kind, "value": value, "from": from_, "to": to}
    if s.get("id") is not None:
        step["id"] = s["id"]
    if s.get("tone") is not None:
        step["tone"] = s["tone"]
    return step


def resolve_waterfall(steps: list[dict], opts: dict) -> dict:
    """lib/charts-waterfall.ts:41-73 resolveWaterfall()."""
    if not isinstance(steps, list) or len(steps) < 2:
        fail("waterfall", "needs at least two steps (a start and a change)")
    check_ids("waterfall", [s.get("id") for s in steps], opts.get("id"))
    level = 0.0
    out: list[dict] = []
    for i, s in enumerate(steps):
        label = check_text("waterfall", f"step {i + 1}'s label", s["label"])
        kind = s.get("kind") if s.get("kind") is not None else ("start" if i == 0 else "delta")
        if kind not in KINDS:
            fail("waterfall", f'step "{label}": kind must be one of {", ".join(KINDS)} (got {kind})')
        if kind == "start" and i != 0:
            fail("waterfall", f"step \"{label}\": only the first step can be the 'start'")
        if kind in ("subtotal", "total") and i == 0:
            fail("waterfall", f'step "{label}": a {kind} adds up the steps before it, so it cannot be the first step')
        if s.get("tone") is not None and s["tone"] not in ("accent", "danger", "muted", "text"):
            fail("waterfall", f'step "{label}": tone must be accent, danger, muted or text')
        if kind in ("delta", "start"):
            v = finite_num("waterfall", f"step \"{label}\"'s value", s.get("value"))
            if kind == "start":
                level = v
                out.append(_mk_step(label, kind, v, 0, v, s))
                continue
            from_ = level
            level = level + v
            out.append(_mk_step(label, kind, v, from_, level, s))
            continue
        if s.get("value") is not None:
            v = finite_num("waterfall", f"step \"{label}\"'s value", s["value"])
            if abs(v - level) > 1e-9 * max(1, abs(level), abs(v)):
                fail("waterfall", f'the {kind} "{label}" is {num_text(v)}, but the steps before it add up to {num_text(to_precision(level, 12))}')
        v = to_precision(level, 12)
        out.append(_mk_step(label, kind, v, 0, v, s))
    for r in out:
        r["from"] = to_precision(r["from"], 12)
        r["to"] = to_precision(r["to"], 12)
    direction = opts.get("dir")
    if direction is not None and direction not in ("v", "h"):
        fail("waterfall", f"dir must be 'v' or 'h' (got {direction})")
    if opts.get("axisGroup") is not None and opts["axisGroup"] is not False:
        fail("waterfall", f"axisGroup must be false (this chart's axis is its own) or left out (got {json.dumps(opts['axisGroup'])})")
    domain = check_domain("waterfall", opts.get("domain"))
    plot_inset = check_inset("waterfall", opts.get("plotInset"))
    if plot_inset and (direction or "v") != "h":
        fail("waterfall", "plotInset is for dir: 'h' (a vertical waterfall has a plot height to line up, not a left and right inset)")
    spec: dict = {"steps": out, "unit": opts.get("unit") or "", "axis": opts.get("axis") is not False, "connectors": opts.get("connectors") is not False, "dir": direction or "v"}
    if domain:
        spec["domain"] = domain
    if plot_inset:
        spec["plotInset"] = plot_inset
    if opts.get("axisGroup") is False:
        spec["axisGroup"] = False
    waterfall_scale(spec)  # a domain smaller than the data fails here, where the chart is written
    return spec


def _step_text(s: dict, unit: str) -> str:
    if s["kind"] == "delta":
        return f"{signed_text(s['value'])}{unit}"
    return f"{num_text(s['value'])}{unit}"


def waterfall_alt(spec: dict) -> str:
    """lib/charts-waterfall.ts:77-79 waterfallAlt()."""
    parts = [f"{s['label']} {_step_text(s, spec['unit'])}" for s in spec["steps"]]
    return f"ウォーターフォール図: {'、'.join(parts)}"


def waterfall_scale(spec: dict) -> dict:
    """lib/charts-waterfall.ts:82-83 waterfallScale()."""
    vs = [v for s in spec["steps"] for v in (s["from"], s["to"])]
    lo = min([0, *vs])
    hi = max([0, *vs])
    return value_scale("waterfall", lo, hi, spec.get("domain"))


def _fill_of(s: dict) -> str:
    if s.get("tone") is not None:
        return s["tone"]
    if s["kind"] == "delta":
        return "danger" if s["value"] < 0 else "accent"
    return FILL[s["kind"]]


def layout_waterfall(spec: dict, g: dict) -> dict:
    """lib/charts-waterfall.ts:95-156 layoutWaterfall()."""
    if spec["dir"] == "h":
        return _layout_waterfall_h(spec, g)
    size = g["size"]
    n = len(spec["steps"])
    c = Canvas(g["x"], g["y"], g["w"], g["height"] if g.get("height") is not None else 320, size, g["widthOf"], g["wrap"])
    los = [v for s in spec["steps"] for v in (s["from"], s["to"])]
    lo = min([0, *los])
    sc = waterfall_scale(spec)
    ticks = [{"v": t, "s": num_text(t)} for t in sc["ticks"]] if spec["axis"] else []
    tick_w = max([0.0] + [c.tw(t["s"]) for t in ticks])
    plot_l = g["x"] + (tick_w + 18 if spec["axis"] else 8)
    plot_r = g["x"] + g["w"] - 8
    slot = (plot_r - plot_l) / n
    if slot < size * 2.2:
        fail("waterfall", f"{n} steps do not fit in {js_round(g['w'])}px (raise width, or use fewer steps)")
    bw = min(72, math.floor(slot * 0.62))
    cats = [c.wrap(s["label"], slot - 8, s["kind"] != "delta") for s in spec["steps"]]
    for i, ls in enumerate(cats):
        for l in ls:
            if c.tw(l, spec["steps"][i]["kind"] != "delta") > slot - 4:
                fail("waterfall", f'the label "{spec["steps"][i]["label"]}" is too long for a column {js_round(slot)}px wide (shorten it, or raise width)')
    cat_h = max(len(l) for l in cats) * c.line_h() + 6
    if g.get("height") is None:
        c.h = 300 + cat_h
    plot_t = g["y"] + 4
    plot_b = g["y"] + c.h - cat_h - 6
    y_top = plot_t + size + 12
    y_bot = plot_b - size - 12
    if y_bot - y_top < 80:
        fail("waterfall", "the figure is too short for its labels; raise height")

    def y_of(v: float) -> float:
        return y_bot - (v - sc["min"]) / (sc["max"] - sc["min"]) * (y_bot - y_top)

    r1 = round1

    shown = thin_ticks(ticks, y_of, lambda t: size + 2, 2)
    for t in ticks:
        y = r1(y_of(t["v"]))
        c.line(plot_l - 6, y, plot_r, y, {"stroke": "text" if t["v"] == 0 else "border"})
        if t in shown:
            c.text(t["s"], plot_l - 10, c.mid(y), "end", "muted")
    if not spec["axis"] and lo < 0:
        c.line(plot_l, r1(y_of(0)), plot_r, r1(y_of(0)), {"stroke": "text"})
    elif not spec["axis"]:
        c.line(plot_l, r1(y_of(0)), plot_r, r1(y_of(0)), {"stroke": "border"})
    if spec["axis"]:
        c.line(plot_l, r1(y_of(sc["max"])), plot_l, r1(y_of(sc["min"])), {"stroke": "border"})

    bars = []
    for i, s in enumerate(spec["steps"]):
        cx = plot_l + (i + 0.5) * slot
        a = y_of(max(s["from"], s["to"]))
        b = y_of(min(s["from"], s["to"]))
        top = a - 1 if abs(b - a) < 2 else a
        bh = max(2, b - a)
        x = r1(cx - bw / 2)
        key = s.get("id") or f"#{i}"
        fill = _fill_of(s)
        solid = c.rect(x, r1(top), bw, r1(bh), {"fill": fill, "id": s.get("id"), "of": key, "solid": s.get("id") or f'bar "{s["label"]}"'})
        bars.append({"s": s, "i": i, "cx": cx, "x": x, "top": top, "h": bh, "solid": solid, "fill": fill, "key": key})

    if spec["connectors"]:
        for i, b in enumerate(bars):
            if i == n - 1:
                break
            y = r1(y_of(b["s"]["to"]))
            c.line(b["x"] + bw, y, bars[i + 1]["x"], y, {"stroke": "muted", "dash": "4,3", "avoid": True, "sw": 2})

    for b in bars:
        text = _step_text(b["s"], spec["unit"])
        up = b["s"]["value"] >= 0
        above = {"x": b["cx"], "y": b["top"] - 7, "anchor": "middle"}
        below = {"x": b["cx"], "y": b["top"] + b["h"] + size + 5, "anchor": "middle"}
        cands = [above, below] if up else [below, above]
        inside = {"x": b["cx"], "y": c.mid(b["top"] + b["h"] / 2), "anchor": "middle"}
        fits = b["h"] >= size + 8 and c.tw(text, True) <= bw - 8
        on = {"fill": b["fill"] if b["fill"] in ("text", "accent", "danger", "muted") else "text"}
        out = c.place(text, cands, "text" if b["fill"] == "muted" else b["fill"], {"bold": True, "of": b["key"]})
        if out is None and fits:
            out = c.text(text, inside["x"], inside["y"], "middle", "bg", {"bold": True, "of": b["key"], "on": on, "host": b["solid"]})
        if out is None:
            fail("waterfall", f'the value "{text}" of "{b["s"]["label"]}" has no room (raise width / height, or shorten the unit)')

    for i, ls in enumerate(cats):
        c.lines(ls, plot_l + (i + 0.5) * slot, plot_b + size + 8, "middle", "text", {"bold": spec["steps"][i]["kind"] != "delta", "of": spec["steps"][i].get("id") or f"#{i}"})

    return c.done()


def _layout_waterfall_h(spec: dict, g: dict) -> dict:
    """lib/charts-waterfall.ts:159-194 layoutWaterfallH()."""
    size = g["size"]
    n = len(spec["steps"])
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    lh = c.line_h()

    r1 = round1

    los = [v for s in spec["steps"] for v in (s["from"], s["to"])]
    lo = min([0, *los])
    sc = waterfall_scale(spec)
    ticks = [{"v": t, "s": num_text(t)} for t in sc["ticks"]] if spec["axis"] else []
    texts = [_step_text(s, spec["unit"]) for s in spec["steps"]]
    val_w = max(c.tw(t, True) for t in texts) + 12
    label_w = min(max(c.tw(s["label"], s["kind"] != "delta") for s in spec["steps"]) + 14, g["w"] * 0.3)
    cats = [c.wrap(s["label"], label_w - 14, s["kind"] != "delta") for s in spec["steps"]]
    inset_l, inset_r = inset_or_need("waterfall", spec.get("plotInset"), label_w + val_w, val_w + 8)
    plot_l = g["x"] + inset_l
    plot_r = g["x"] + g["w"] - inset_r
    if plot_r - plot_l < 120:
        fail("waterfall", "the figure is too narrow for its labels (raise width, shorten the labels / unit)")
    bar_h = max(24, size + 10)
    pitch = max(bar_h + 14, max(len(l) * lh + 8 for l in cats))
    axis_h = size + 14 if spec["axis"] else 6
    c.h = g["height"] if g.get("height") is not None else n * pitch + axis_h + 8
    if g.get("height") is not None and g["height"] < n * pitch + axis_h:
        fail("waterfall", f"height {g['height']} is too small for {n} steps (need at least {n * pitch + axis_h})")
    y0 = g["y"] + 4
    body_b = y0 + n * pitch

    def x_of(v: float) -> float:
        return plot_l + (v - sc["min"]) / (sc["max"] - sc["min"]) * (plot_r - plot_l)

    shown = thin_ticks(ticks, x_of, lambda t: c.tw(t["s"]), 12)
    for t in ticks:
        x = r1(x_of(t["v"]))
        c.line(x, y0, x, body_b + 6, {"stroke": "text" if t["v"] == 0 else "border"})
        if t in shown:
            c.text(t["s"], x, body_b + size + 10, "middle", "muted")
    if not spec["axis"]:
        c.line(r1(x_of(0)), y0, r1(x_of(0)), body_b, {"stroke": "text" if lo < 0 else "border"})

    bars = []
    for i, s in enumerate(spec["steps"]):
        cy = y0 + (i + 0.5) * pitch
        key = s.get("id") or f"#{i}"
        x1, x2 = x_of(min(s["from"], s["to"])), x_of(max(s["from"], s["to"]))
        w = max(2, x2 - x1)
        rx = x1 - 1 if abs(x2 - x1) < 2 else x1
        solid = c.rect(r1(rx), r1(cy - bar_h / 2), r1(w), bar_h, {"fill": _fill_of(s), "id": s.get("id"), "of": key, "solid": s.get("id") or f'bar "{s["label"]}"'})
        ls = cats[i]
        c.lines(ls, g["x"] + label_w - 10, cy - (len(ls) - 1) * lh / 2 + size * 0.36, "end", "text", {"bold": s["kind"] != "delta", "of": key})
        bars.append({"s": s, "i": i, "cy": cy, "x1": x1, "x2": x2, "solid": solid, "key": key, "fill": _fill_of(s)})

    if spec["connectors"]:
        for i, b in enumerate(bars):
            if i == n - 1:
                break
            x = r1(x_of(b["s"]["to"]))
            c.line(x, b["cy"] + bar_h / 2, x, bars[i + 1]["cy"] - bar_h / 2, {"stroke": "muted", "dash": "4,3", "avoid": True})

    for b in bars:
        text = texts[b["i"]]
        right = b["s"]["value"] >= 0
        r = {"x": b["x2"] + 7, "y": c.mid(b["cy"]), "anchor": "start"}
        l = {"x": b["x1"] - 7, "y": c.mid(b["cy"]), "anchor": "end"}
        fits = c.tw(text, True) <= abs(b["x2"] - b["x1"]) - 10
        on = {"fill": b["fill"]}
        out = c.place(text, [r, l] if right else [l, r], "text" if b["fill"] == "muted" else b["fill"], {"bold": True, "of": b["key"]})
        if out is None and fits:
            out = c.text(text, (b["x1"] + b["x2"]) / 2, c.mid(b["cy"]), "middle", "bg", {"bold": True, "of": b["key"], "on": on, "host": b["solid"]})
        if out is None:
            fail("waterfall", f'the value "{text}" of "{b["s"]["label"]}" has no room (raise width, or shorten the unit)')

    return c.done()


def waterfall_band(steps: list[dict], opts: dict | None = None) -> ChartBand:
    """lib/charts-dsl.ts:51-54 waterfallBand() + lib/dsl/charts.ts's waterfall()."""
    opts = opts or {}
    spec = resolve_waterfall(steps, opts)
    opt_alt = opts.get("alt")
    alt = opt_alt if opt_alt is not None else waterfall_alt(spec)
    return ChartBand(kind="waterfall", spec=spec, alt=alt, **common_chart_opts("waterfall", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
