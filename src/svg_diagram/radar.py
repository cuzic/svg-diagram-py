"""1:1 port of lib/charts-radar.ts's layoutRadar() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the radar() DSL constructor (lib/charts-dsl.ts's
radarBand()) — defaults + the structural validations that affect layout.

radarTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
heatmapTexts()/sankeyTexts().

Golden master: lib/charts-radar.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .charts_base import Canvas, ChartBand, check_ids, check_text, common_chart_opts, fail, finite_num, nice_near, nice_scale, num_text, overlaps
from .charts_base import _to_precision as to_precision
from .emit_common import js_num, js_round, round1

SERIES_STYLES: list[dict] = [
    {"tone": "accent", "marker": "circle"},
    {"tone": "text", "dash": "8,5", "marker": "square"},
    {"tone": "danger", "dash": "2,5", "marker": "diamond"},
    {"tone": "muted", "dash": "10,4,2,4", "marker": "triangle"},
]


def marker_path(shape: str, x: float, y: float, r: float = 5) -> str:
    """lib/charts-radar.ts:34-42 markerPath()."""

    def f(v: float) -> str:
        return js_num(js_round(v * 10) / 10)

    if shape == "circle":
        return f"M{f(x - r)},{f(y)} a{js_num(r)},{js_num(r)} 0 1 0 {js_num(2 * r)},0 a{js_num(r)},{js_num(r)} 0 1 0 {js_num(-2 * r)},0 Z"
    if shape == "square":
        return f"M{f(x - r)},{f(y - r)} H{f(x + r)} V{f(y + r)} H{f(x - r)} Z"
    if shape == "diamond":
        return f"M{f(x)},{f(y - r - 1)} L{f(x + r + 1)},{f(y)} L{f(x)},{f(y + r + 1)} L{f(x - r - 1)},{f(y)} Z"
    return f"M{f(x)},{f(y - r - 1)} L{f(x + r + 1)},{f(y + r)} L{f(x - r - 1)},{f(y + r)} Z"


def resolve_radar(axes: list[str], series: list[dict], opts: dict) -> dict:
    """lib/charts-radar.ts:44-64 resolveRadar()."""
    if not isinstance(axes, list) or not (3 <= len(axes) <= 12):
        fail("radar", f"needs 3 to 12 axes (got {len(axes) if isinstance(axes, list) else 0})")
    if not isinstance(series, list) or not (1 <= len(series) <= 4):
        fail("radar", f"needs 1 to 4 series (got {len(series) if isinstance(series, list) else 0}; more cannot be told apart)")
    for i, a in enumerate(axes):
        check_text("radar", f"axis {i + 1}'s label", a)
    check_ids("radar", [s.get("id") for s in series], opts.get("id"))
    min_v = finite_num("radar", "min", opts.get("min") if opts.get("min") is not None else 0)
    for s in series:
        check_text("radar", "a series label", s["label"])
        if not isinstance(s.get("values"), list) or len(s["values"]) != len(axes):
            fail("radar", f'series "{s["label"]}" has {len(s["values"]) if isinstance(s.get("values"), list) else 0} values for {len(axes)} axes')
        for i, v in enumerate(s["values"]):
            if finite_num("radar", f'"{s["label"]}" on "{axes[i]}"', v) < min_v:
                fail("radar", f'"{s["label"]}" on "{axes[i]}" is {v}, below min {min_v} (set min lower)')
    data_max = max(v for s in series for v in s["values"])
    if opts.get("max") is not None:
        max_v = finite_num("radar", "max", opts["max"])
    else:
        max_v = nice_scale(min_v, max(data_max, min_v + 1), 4)["max"]
    if not (max_v > min_v):
        fail("radar", f"max ({max_v}) must be above min ({min_v})")
    if data_max > max_v:
        fail("radar", f"a value ({data_max}) is above max ({max_v})")
    step_k = nice_near((max_v - min_v) / 4)
    nat = (max_v - min_v) / step_k
    if opts.get("rings") is not None:
        rings = opts["rings"]
    else:
        rings = js_round(nat) if (abs(nat - js_round(nat)) < 1e-9 and nat >= 3 and nat <= 6) else 4
    if not (isinstance(rings, int) and not isinstance(rings, bool) and 2 <= rings <= 8):
        fail("radar", f"rings must be a whole number from 2 to 8 (got {rings})")
    return {
        "axes": list(axes),
        "series": [{**s, "values": list(s["values"])} for s in series],
        "min": min_v, "max": max_v, "rings": rings,
        "values": bool(opts.get("values")), "unit": opts.get("unit") or "",
        "fill": opts.get("fill") if opts.get("fill") is not None else len(series) == 1,
    }


def radar_alt(s: dict) -> str:
    """lib/charts-radar.ts:65-67 radarAlt()."""
    series_parts = []
    for x in s["series"]:
        vals = "、".join(f"{s['axes'][i]} {num_text(v)}{s['unit']}" for i, v in enumerate(x["values"]))
        series_parts.append(f"{x['label']}: {vals}")
    return f"レーダーチャート（軸: {'、'.join(s['axes'])}）。{'。'.join(series_parts)}"


def _ring_value(s: dict, k: int) -> float:
    return to_precision(s["min"] + (s["max"] - s["min"]) * k / s["rings"], 6)


def layout_radar(s: dict, g: dict) -> dict:
    """lib/charts-radar.ts:77-175 layoutRadar()."""
    size = g["size"]
    n = len(s["axes"])
    c = Canvas(g["x"], g["y"], g["w"], g["height"] if g.get("height") is not None else 400, size, g["widthOf"], g["wrap"])
    lh = c.line_h()

    items = [{"x": x, "i": i, "w": 34 + 8 + c.tw(x["label"]) + 24} for i, x in enumerate(s["series"])]
    rows: list[list[dict]] = [[]]
    rw = 0.0
    for it in items:
        if rw + it["w"] - 24 > g["w"] and rows[-1]:
            rows.append([])
            rw = 0
        rows[-1].append(it)
        rw += it["w"]
    legend_h = len(rows) * (lh + 6) + 8

    cx = g["x"] + g["w"] / 2

    r1 = round1

    def ang(i: int) -> float:
        return -math.pi / 2 + 2 * math.pi * i / n

    def name_at(i: int, radius: float, cy: float, ls: list[str]) -> dict:
        cs, sn = math.cos(ang(i)), math.sin(ang(i))
        px, py = cx + cs * radius, cy + sn * radius
        h = len(ls) * lh
        anchor = "start" if cs > 0.3 else ("end" if cs < -0.3 else "middle")
        x = px + cs * 14
        top = py - h / 2 if abs(sn) <= 0.3 else (py + sn * 14 - (0 if sn > 0.3 else h))
        w = max(c.tw(t, True) for t in ls)
        box_x = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        return {"x": x, "base": top + size, "anchor": anchor, "box": {"x": box_x, "y": top, "w": w, "h": (len(ls) - 1) * lh + size + 4}}

    natural_w = max(c.tw(a, True) for a in s["axes"])
    plan = None
    for max_w in (min(g["w"] * 0.26, natural_w), min(g["w"] * 0.18, natural_w), min(g["w"] * 0.12, natural_w), 44):
        labels = [c.wrap(a, max_w + 2, True) for a in s["axes"]]
        lab_h = max(len(l) for l in labels) * lh
        side_w = max(max(c.tw(t, True) for t in l) for l in labels) + 14
        v_pad = lab_h + 22
        h = g["height"] if g.get("height") is not None else max(400, 2 * (v_pad + 130) + legend_h)
        area_h = h - legend_h
        radius = min((area_h - 2 * v_pad) / 2, (g["w"] / 2) - side_w - 12)
        cy = g["y"] + area_h / 2
        if radius < 60:
            continue
        boxes = [name_at(i, radius, cy, ls)["box"] for i, ls in enumerate(labels)]
        if any(overlaps(b, o) for i, b in enumerate(boxes) for o in boxes[i + 1 :]):
            continue
        plan = {"labels": labels, "R": radius, "cy": cy}
        c.h = h
        break
    if plan is None:
        fail("radar", "the figure is too small for its axis names (raise width / height, shorten the names, or use fewer axes)")
    labels, radius, cy = plan["labels"], plan["R"], plan["cy"]
    area_h = c.h - legend_h

    def at(i: int, f: float) -> dict:
        return {"x": cx + math.cos(ang(i)) * radius * f, "y": cy + math.sin(ang(i)) * radius * f}

    def poly(f: float) -> str:
        pts = [at(i, f) for i in range(n)]
        return "M" + " L".join(f"{js_num(r1(p['x']))},{js_num(r1(p['y']))}" for p in pts) + " Z"

    for k in range(1, s["rings"] + 1):
        c.path(poly(k / s["rings"]), {"fill": "none", "stroke": "border", "sw": 2})
    for i in range(n):
        p = at(i, 1)
        c.line(cx, cy, p["x"], p["y"], {"stroke": "border"})

    polys = [[at(i, (v - s["min"]) / (s["max"] - s["min"])) for i, v in enumerate(x["values"])] for x in s["series"]]
    for k, x in enumerate(s["series"]):
        st = SERIES_STYLES[k]
        pts = polys[k]
        d = "M" + " L".join(f"{js_num(r1(p['x']))},{js_num(r1(p['y']))}" for p in pts) + " Z"
        of_id = x.get("id") or f"#{k}"
        if s["fill"]:
            c.path(d, {"fill": st["tone"], "op": 0.14, "of": of_id})
        c.path(d, {"fill": "none", "stroke": st["tone"], "sw": 3, "dash": st.get("dash"), "of": of_id})
        for i, p in enumerate(pts):
            q = pts[(i + 1) % n]
            c.segs.append({"x1": p["x"], "y1": p["y"], "x2": q["x"], "y2": q["y"]})
        if x.get("id"):
            xs = [p["x"] for p in pts]
            ys = [p["y"] for p in pts]
            c.anchors.append({"id": x["id"], "x": min(xs), "y": min(ys), "w": max(xs) - min(xs), "h": max(ys) - min(ys)})

    for k, x in enumerate(s["series"]):
        st = SERIES_STYLES[k]
        of_id = x.get("id") or f"#{k}"
        for p in polys[k]:
            c.path(marker_path(st["marker"], p["x"], p["y"]), {"fill": "bg", "stroke": st["tone"], "sw": 2.5, "of": of_id})
            c.marks.append({"x": p["x"] - 7, "y": p["y"] - 7, "w": 14, "h": 14})

    for i in range(n):
        q = name_at(i, radius, cy, labels[i])
        c.lines(labels[i], q["x"], q["base"], q["anchor"], "text", {"bold": True})

    min_step = max(1, math.ceil((size + 6) / (radius / s["rings"])))
    tick_texts = [{"k": j + 1, "s": num_text(_ring_value(s, j + 1))} for j in range(s["rings"]) if (s["rings"] - (j + 1)) % min_step == 0]
    best_ticks: list[dict] = []
    for sp in range(n):
        right = math.cos(ang(sp)) >= -1e-9
        dx = 9 if right else -9
        anchor = "start" if right else "end"
        got: list[dict] = []
        put: list[dict] = []
        for t in reversed(tick_texts):
            p = at(sp, t["k"] / s["rings"])
            for y in (c.mid(p["y"]), c.mid(p["y"]) - js_round(size * 0.7), c.mid(p["y"]) + js_round(size * 0.7)):
                r = c.box_of(t["s"], js_round(p["x"] + dx), y, anchor)
                if not c.free(r) or any(overlaps(r, o) for o in got):
                    continue
                got.append(r)
                put.append({"s": t["s"], "x": p["x"] + dx, "y": y, "anchor": anchor})
                break
        if len(put) > len(best_ticks):
            best_ticks = put
        if len(put) == len(tick_texts):
            break
    for t in best_ticks:
        c.text(t["s"], t["x"], t["y"], t["anchor"], "muted")

    if s["values"]:
        for k, x in enumerate(s["series"]):
            for i, v in enumerate(x["values"]):
                p = polys[k][i]
                text = f"{num_text(v)}{s['unit']}"
                cs, sn = math.cos(ang(i)), math.sin(ang(i))
                # lib/charts-radar.ts:153-156: `[14, 22, 32].flatMap(d => [dCand, F1, F2, F3, F4])`
                # — the 4 fixed candidates (which don't depend on `d`) are interleaved AFTER
                # EACH d-candidate, not appended once at the end.
                anchor = "start" if cs > 0.3 else ("end" if cs < -0.3 else "middle")
                y_off = size * 0.9 if sn > 0.3 else (-2 if sn < -0.3 else size * 0.36)
                fixed = [
                    {"x": p["x"] + 10, "y": p["y"] - 10, "anchor": "start"},
                    {"x": p["x"] - 10, "y": p["y"] - 10, "anchor": "end"},
                    {"x": p["x"] + 10, "y": p["y"] + size + 8, "anchor": "start"},
                    {"x": p["x"] - 10, "y": p["y"] + size + 8, "anchor": "end"},
                ]
                cands = []
                for d in (14, 22, 32):
                    cands.append({"x": p["x"] + cs * d, "y": p["y"] + sn * d + y_off, "anchor": anchor})
                    cands.extend(fixed)
                st = SERIES_STYLES[k]
                tone = "text" if st["tone"] == "muted" else st["tone"]
                of_id = x.get("id") or f"#{k}"
                if not c.place(text, cands, tone, {"bold": True, "of": of_id}):
                    c.omitted.append(f"{x['label']} {s['axes'][i]} {text}")

    ly = g["y"] + area_h + 6
    for row in rows:
        lx = g["x"] + (g["w"] - sum(it["w"] for it in row) + 24) / 2
        for it in row:
            st = SERIES_STYLES[it["i"]]
            my = ly + lh / 2 - 1
            of_id = it["x"].get("id") or f"#{it['i']}"
            c.line(lx, my, lx + 30, my, {"stroke": st["tone"], "sw": 3, "dash": st.get("dash"), "of": of_id})
            c.path(marker_path(st["marker"], lx + 15, my), {"fill": "bg", "stroke": st["tone"], "sw": 2.5, "of": of_id})
            c.text(it["x"]["label"], lx + 38, c.mid(my), "start", "text", {"of": of_id})
            lx += it["w"]
        ly += lh + 6

    return c.done()


def radar_band(axes: list[str], series: list[dict], opts: dict | None = None) -> ChartBand:
    """lib/charts-dsl.ts:71-74 radarBand() + lib/dsl/charts.ts's radar()."""
    opts = opts or {}
    spec = resolve_radar(axes, series, opts)
    alt = opts.get("alt") if opts.get("alt") is not None else radar_alt(spec)
    return ChartBand(kind="radar", spec=spec, alt=alt, **common_chart_opts("radar", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
