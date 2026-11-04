"""1:1 port of lib/plane.ts's layoutPlane() (exported, golden-tested live) and
lib/emit-figures.ts's renderPlane(), plus the plane() DSL constructor
(lib/dsl/figures.ts). This is a standalone band type ("plane"), NOT part of the "chart"
band family (lib/charts.ts) — it has its own layout/render pair, not charts.layout_chart().

Stage/reveal visibility (`visibleAt`) is not ported: this port's bands never set a `stage`,
so every line/path/dim/point/text is always visible, same scope decision as every other
band in this port.

Known floating-point caveat: every path's arrow-tip direction (and centripetal_curves(),
used for a smooth path whose x does not increase monotonically) normalizes a vector via
`hypot(...)`; V8's `Math.hypot` and CPython's `math.hypot` are different native
implementations and can disagree in the last ULP, so `LaidOutPlane.paths[].tip`,
and occasionally a curve point, may differ from Node's by ~1e-15 — far below anything
js_round()'s 0.1px display rounding would ever show (render_plane()'s output is confirmed
byte-identical even where this shows up in the pre-render layout data). Tests compare
`paths` with a tolerance for exactly this reason; every other field matches exactly.

Golden master: lib/plane.ts + lib/dsl/figures.ts + lib/emit-figures.ts's renderPlane()
(Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import text_width
from .charts_base import overlaps
from .emit_common import emoji_span, js_num, js_round, snap4
from .tokens import PALETTE, text_color_of

TICK = 6
DIM_OFFSET = 26
DIM_CHIP_PAD = 6


def _sig_round(n: float, p: int) -> float:
    """Rounds `n` to `p` significant digits (JS `parseFloat(n.toPrecision(p))`)."""
    if n == 0:
        return 0.0
    d = p - 1 - math.floor(math.log10(abs(n)))
    factor = 10.0**d
    rounded = math.floor(abs(n) * factor + 0.5) / factor
    return rounded if n >= 0 else -rounded


def fmt(n: float) -> str:
    """lib/plane.ts:46 fmt()."""
    return js_num(_sig_round(n, 3))


def _nice_step(rng: float) -> float:
    """lib/plane.ts:47-50 niceStep()."""
    raw = rng / 6
    mag = 10 ** math.floor(math.log10(raw))
    f = raw / mag
    if f < 1.5:
        return mag * 1
    if f < 3.5:
        return mag * 2
    if f < 7.5:
        return mag * 5
    return mag * 10


def ticks_of(axis: dict, caller: str = "plane") -> list[dict]:
    """lib/plane.ts:51-58 ticksOf(). bars() also calls this (with axis = {"max": band["max"]},
    so categories/ticks/min/step are never set from that caller) — the generic shape is kept
    for bars()'s sake even though plane() itself exercises every branch."""
    if axis.get("categories"):
        return [{"at": i + 1, "label": label} for i, label in enumerate(axis["categories"])]
    if axis.get("ticks"):
        return [({"at": t, "label": fmt(t)} if isinstance(t, (int, float)) else t) for t in axis["ticks"]]
    min_v = axis.get("min", 0)
    step = axis.get("step")
    if step is None:
        step = _nice_step(axis["max"] - min_v)
    if not (step > 0) or not math.isfinite(step):
        raise ValueError(f"{caller}(): an axis step must be a number > 0 (got {axis.get('step')})")
    out = []
    v, i = min_v, 0
    while v <= axis["max"] + step * 1e-9 and i < 200:
        out.append({"at": v, "label": fmt(v)})
        i += 1
        v = min_v + i * step
    return out


def _size_of(band: dict, roles: dict) -> float:
    return roles[band.get("labelRole") or "note"]


def _geom_of(band: dict, roles: dict) -> float:
    return _size_of(band, roles) if band.get("labelRole") else 14


def stage_edges(stages: list, min_v: float, max_v: float) -> list[float]:
    """lib/plane.ts:41-45 stageEdges(). Node's `tos.map(Number)` turns a `to`-less stage's
    `undefined` into `NaN` rather than raising (`Number(undefined)` is `NaN` in JS); mixing
    `to`-having and `to`-less stages is not really a supported/tested shape, but this at
    least matches Node's own (silently broken, not crashing) behavior for it."""
    n = len(stages)
    tos = [None if isinstance(st, str) else st.get("to") for st in stages[:-1]]
    if all(t is None for t in tos):
        return [min_v + (max_v - min_v) * i / n for i in range(n + 1)]
    return [min_v, *(float(t) if t is not None else math.nan for t in tos), max_v]


def monotone_curves(p: list[dict]) -> list[list[dict]]:
    """lib/plane.ts:63-75 monotoneCurves(): monotone cubic (Fritsch-Carlson)."""
    n = len(p)
    dx: list[float] = []
    sec: list[float] = []
    for i in range(n - 1):
        dx.append(p[i + 1]["x"] - p[i]["x"])
        sec.append((p[i + 1]["y"] - p[i]["y"]) / dx[i])
    m: list[float] = [sec[0] if sec else 0]
    for i in range(1, n - 1):
        m.append(0 if sec[i - 1] * sec[i] <= 0 else 2 / (1 / sec[i - 1] + 1 / sec[i]))
    m.append(sec[n - 2] if n >= 2 else 0)
    for i in range(n - 1):
        if sec[i] == 0:
            m[i] = 0
            m[i + 1] = 0
            continue
        a = m[i] / sec[i]
        b = m[i + 1] / sec[i]
        hh = math.hypot(a, b)
        if hh > 3:
            m[i] = 3 * a / hh * sec[i]
            m[i + 1] = 3 * b / hh * sec[i]
    out = []
    for i, d in enumerate(dx):
        out.append([
            {"x": p[i]["x"] + d / 3, "y": p[i]["y"] + m[i] * d / 3},
            {"x": p[i + 1]["x"] - d / 3, "y": p[i + 1]["y"] - m[i + 1] * d / 3},
            p[i + 1],
        ])
    return out


def centripetal_curves(p: list[dict]) -> list[list[dict]]:
    """lib/plane.ts:78-92 centripetalCurves(): centripetal Catmull-Rom (alpha 0.5)."""
    n = len(p)

    def at(i: int) -> dict:
        if i < 0:
            return {"x": 2 * p[0]["x"] - p[1]["x"], "y": 2 * p[0]["y"] - p[1]["y"]}
        if i >= n:
            return {"x": 2 * p[n - 1]["x"] - p[n - 2]["x"], "y": 2 * p[n - 1]["y"] - p[n - 2]["y"]}
        return p[i]

    def d(a: dict, b: dict) -> float:
        return math.hypot(b["x"] - a["x"], b["y"] - a["y"]) ** 0.5

    out = []
    for i in range(n - 1):
        p0, p1, p2, p3 = at(i - 1), p[i], p[i + 1], at(i + 2)
        d1, d2, d3 = d(p0, p1), d(p1, p2), d(p2, p3)

        def c(k: float, a: dict, b: dict, e: dict, f: float, g: float) -> dict:
            return {
                "x": (k * k * e["x"] - g * g * a["x"] + (2 * k * k + 3 * k * f + f * f) * b["x"]) / (3 * k * (k + f)),
                "y": (k * k * e["y"] - g * g * a["y"] + (2 * k * k + 3 * k * f + f * f) * b["y"]) / (3 * k * (k + f)),
            }

        out.append([c(d1, p0, p1, p2, d2, d2), c(d3, p3, p2, p1, d2, d2), p2])
    return out


def bez(a: dict, c1: dict, c2: dict, b: dict, t: float) -> dict:
    """lib/plane.ts:94-97 bez()."""
    u = 1 - t
    return {
        "x": u * u * u * a["x"] + 3 * u * u * t * c1["x"] + 3 * u * t * t * c2["x"] + t * t * t * b["x"],
        "y": u * u * u * a["y"] + 3 * u * u * t * c1["y"] + 3 * u * t * t * c2["y"] + t * t * t * b["y"],
    }


def layout_plane(band: dict, x: float, y: float, w: float, width_of, roles: dict) -> dict:
    """lib/plane.ts:99-367 layoutPlane()."""
    size = _size_of(band, roles)
    g = _geom_of(band, roles)
    half = g * 5 / 14
    label_h = size + 6

    def tw(s: str, weight: int = 400) -> float:
        return text_width(width_of, s, size, weight)

    opt_width = band.get("width")
    width = min(w, opt_width if opt_width is not None else w)
    left = x + (w - width) / 2
    h = band["height"]
    x_min = band["x"].get("min") or 0
    y_min = band["y"].get("min") or 0
    x_span = band["x"]["max"] - x_min
    stages = band.get("stages") or []
    edges = stage_edges(stages, x_min, band["x"]["max"]) if stages else []
    if stages:
        x_ticks = []
        for i, st in enumerate(stages):
            lo = edges[i] if i < len(edges) else x_min
            hi = edges[i + 1] if i + 1 < len(edges) else band["x"]["max"]
            label = st if isinstance(st, str) else st["name"]
            x_ticks.append({"at": (lo + hi) / 2, "label": label})
    else:
        x_ticks = ticks_of(band["x"])
    y_ticks = ticks_of(band["y"])
    if not (x_span > 0) or not (band["y"]["max"] > y_min):
        raise ValueError("plane(): each axis needs max > min")
    y_down = bool(band.get("yDown"))

    y_tick_w = max([0.0] + [tw(t["label"]) for t in y_ticks] + [tw(t) for t in (band.get("yTickSample") or [])])
    pad_l = math.ceil(y_tick_w) + TICK + 14
    last_tick = tw(x_ticks[-1]["label"]) / 2 if x_ticks else 0
    x_label_gap = max(14, math.ceil(last_tick) + 8)
    pad_r = (x_label_gap + math.ceil(tw(band["x"]["label"], 700)) + 8) if band["x"].get("label") else max(16, math.ceil(last_tick) + 4)

    def is_leader(p: dict) -> bool:
        return bool(p.get("labelLeader")) and bool(p.get("label")) and (p.get("labelAt") is None or p.get("labelAt") == "auto") and not p.get("labelOffset")

    def is_end(p: dict) -> bool:
        return bool(band.get("endLabels")) and bool(p.get("label")) and p.get("labelAt") == "right" and not p.get("labelOffset")

    for p in band.get("points") or []:
        if is_leader(p):
            pad_r = max(pad_r, math.ceil(tw(p["label"], 700)) + 10)
    for p in band.get("points") or []:
        if is_end(p):
            t = (p["at"][0] - x_min) / x_span
            if t > 0.05:
                pad_r = max(pad_r, math.ceil((14 + tw(p["label"], 700) - (1 - t) * (width - pad_l)) / t))
    edge = max(14, math.ceil(g / 2) + 7)
    pad_t = g + 26 if y_down else (g + 20 if band["y"].get("label") else edge)
    pad_b = (g + 22 if band["y"].get("label") else edge) if y_down else g + 26
    plot_l = left + pad_l
    plot_r = left + width - pad_r
    plot_t = y + pad_t
    plot_b = y + h - pad_b
    if plot_r - plot_l < 60 or plot_b - plot_t < 60:
        raise ValueError("plane(): the figure is too small for its axes — raise height / width")

    def px(v: float) -> float:
        return plot_l + (v - x_min) / x_span * (plot_r - plot_l)

    def py(v: float) -> float:
        if y_down:
            return plot_t + (v - y_min) / (band["y"]["max"] - y_min) * (plot_b - plot_t)
        return plot_b - (v - y_min) / (band["y"]["max"] - y_min) * (plot_b - plot_t)

    by_id = {p["id"]: p["at"] for p in (band.get("points") or []) if p.get("id")}

    def pos(r):
        if not isinstance(r, str):
            return r
        p = by_id.get(r)
        if p is None:
            raise ValueError(f"plane(): \"{r}\" is not a point id (declare it with points: [{{id: '{r}', at: [x, y]}}])")
        return p

    def pt(r) -> dict:
        vx, vy = pos(r)
        return {"x": px(vx), "y": py(vy)}

    axis_y = plot_t if y_down else plot_b
    axis_x = plot_l
    texts: list[dict] = []
    boxes: list[dict] = []
    obstacles: list[dict] = []

    def ink(what: str, r: dict, dim: int | None = None) -> None:
        item = {"what": what, **r}
        if dim is not None:
            item["dim"] = dim
        obstacles.append(item)

    def ink_seg(what: str, seg: dict, dim: int | None = None) -> None:
        n = max(1, math.ceil(math.hypot(seg["x2"] - seg["x1"], seg["y2"] - seg["y1"]) / 6))
        for i in range(n + 1):
            ink(what, {"x": seg["x1"] + (seg["x2"] - seg["x1"]) * i / n - 2, "y": seg["y1"] + (seg["y2"] - seg["y1"]) * i / n - 2, "w": 4, "h": 4}, dim)

    def add_text(s: str, tx: float, base: float, anchor: str, tone: str, bold: bool = False, reveal: int | None = None) -> None:
        item: dict = {"s": s, "x": tx, "y": base, "anchor": anchor, "tone": tone, "bold": bold}
        if reveal:
            item["reveal"] = reveal
        texts.append(item)
        tww = tw(s, 700 if bold else 400)
        box_x = tx - tww / 2 if anchor == "middle" else (tx - tww if anchor == "end" else tx)
        boxes.append({"label": s, "x": box_x, "y": base - size, "w": tww, "h": label_h})

    ticks: list[dict] = []
    for t in x_ticks:
        tx = px(t["at"])
        if not stages:
            tick = {"x1": tx, "y1": axis_y, "x2": tx, "y2": axis_y + (-TICK if y_down else TICK)}
            ticks.append(tick)
            ink_seg("a tick mark", tick)
        add_text(t["label"], tx, axis_y - TICK - 8 if y_down else axis_y + TICK + g + 2, "middle", "muted")
    for t in y_ticks:
        ty = py(t["at"])
        tick = {"x1": axis_x, "y1": ty, "x2": axis_x - TICK, "y2": ty}
        ticks.append(tick)
        ink_seg("a tick mark", tick)
        add_text(t["label"], axis_x - TICK - 6, ty + half, "end", "muted")

    ink("the x axis", {"x": axis_x, "y": axis_y - 2, "w": plot_r - axis_x, "h": 4})
    ink("the y axis", {"x": axis_x - 2, "y": plot_t, "w": 4, "h": plot_b - plot_t})
    ink("the x axis arrow", {"x": plot_r - 10, "y": axis_y - 5, "w": 12, "h": 10})
    if y_down:
        ink("the y axis arrow", {"x": axis_x - 5, "y": plot_b - 10, "w": 10, "h": 12})
    else:
        ink("the y axis arrow", {"x": axis_x - 5, "y": plot_t - 2, "w": 10, "h": 12})

    grid: list[dict] = []
    if band.get("grid"):
        for t in ([] if stages else x_ticks):
            grid.append({"x1": px(t["at"]), "y1": plot_t, "x2": px(t["at"]), "y2": plot_b})
        for t in y_ticks:
            grid.append({"x1": plot_l, "y1": py(t["at"]), "x2": plot_r, "y2": py(t["at"])})

    if band["x"].get("label"):
        add_text(band["x"]["label"], plot_r + x_label_gap, axis_y + half, "start", "muted", True)
    if band["y"].get("label"):
        add_text(band["y"]["label"], axis_x - 4, plot_b + g + 14 if y_down else plot_t - 14, "start", "muted", True)

    def spot(side: str, q: dict) -> dict:
        if side == "right":
            return {"anchor": "start", "x": q["x"] + 12, "base": q["y"] + half}
        if side == "left":
            return {"anchor": "end", "x": q["x"] - 12, "base": q["y"] + half}
        if side == "above":
            return {"anchor": "middle", "x": q["x"], "base": q["y"] - 14}
        if side == "below":
            return {"anchor": "middle", "x": q["x"], "base": q["y"] + g + 12}
        if side == "above-right":
            return {"anchor": "start", "x": q["x"] + 10, "base": q["y"] - 12}
        if side == "above-left":
            return {"anchor": "end", "x": q["x"] - 10, "base": q["y"] - 12}
        if side == "below-right":
            return {"anchor": "start", "x": q["x"] + 10, "base": q["y"] + g + 10}
        return {"anchor": "end", "x": q["x"] - 10, "base": q["y"] + g + 10}

    sides = ["right", "left", "above", "below", "above-right", "above-left", "below-right", "below-left"]
    end_labels: list[dict] = []
    auto_labels: list[dict] = []
    points: list[dict] = []
    for p in band.get("points") or []:
        q = pt(p["at"])
        tone = p.get("tone") or "accent"
        if p.get("label"):
            side = "right" if (p.get("labelAt") is None or p.get("labelAt") == "auto") else p["labelAt"]
            sp = spot(side, q)
            ox, oy = p.get("labelOffset") or (0, 0)
            if p.get("labelAt") is None or p.get("labelAt") == "auto":
                if not p.get("labelOffset") and not is_end(p):
                    auto_labels.append({"text": len(texts), "box": len(boxes), "q": q, "label": p["label"], "bold": True, "first": side, "leader": is_leader(p)})
            add_text(p["label"], sp["x"] + ox, sp["base"] + oy, sp["anchor"], tone, True, p.get("reveal"))
        if is_end(p):
            end_labels.append({"text": len(texts) - 1, "box": len(boxes) - 1, "y": q["y"]})
        ink("a point", {"x": q["x"] - 7, "y": q["y"] - 7, "w": 14, "h": 14})
        item: dict = {"x": q["x"], "y": q["y"], "tone": tone, "shape": p.get("shape") or "dot"}
        if p.get("reveal"):
            item["reveal"] = p["reveal"]
        points.append(item)

    lines: list[dict] = []
    for l in band.get("lines") or []:
        a = pt(l["from"])
        b = pt(l["to"])
        ink_seg("a guide line", {"x1": a["x"], "y1": a["y"], "x2": b["x"], "y2": b["y"]})
        if l.get("arrow"):
            length = math.hypot(b["x"] - a["x"], b["y"] - a["y"]) or 1
            ux, uy = (b["x"] - a["x"]) / length, (b["y"] - a["y"]) / length
            xs = [b["x"], b["x"] - ux * 10 - uy * 5, b["x"] - ux * 10 + uy * 5]
            ys = [b["y"], b["y"] - uy * 10 + ux * 5, b["y"] - uy * 10 - ux * 5]
            ink("a guide line arrow", {"x": min(xs), "y": min(ys), "w": max(xs) - min(xs), "h": max(ys) - min(ys)})
        item = {"x1": a["x"], "y1": a["y"], "x2": b["x"], "y2": b["y"], "tone": l.get("tone") or "muted", "dashed": l.get("dashed") if l.get("dashed") is not None else (not stages), "arrow": bool(l.get("arrow"))}
        if l.get("reveal"):
            item["reveal"] = l["reveal"]
        lines.append(item)

    for i in range(1, len(stages)):
        dx_ = px(edges[i])
        seg = {"x1": dx_, "y1": plot_t, "x2": dx_, "y2": plot_b}
        ink_seg("a stage divider", seg)
        lines.append({**seg, "tone": "muted", "dashed": True, "arrow": False})

    clashes: list[str] = []
    pts_list = band.get("points") or []

    def name_of(p: dict) -> str:
        return p.get("label") or p.get("id") or "a point"

    dots = [{**pt(p["at"]), "owner": i, "target": False, "name": name_of(p)} for i, p in enumerate(pts_list)]
    for i, p in enumerate(pts_list):
        if not p.get("evolves"):
            continue
        a = pt(p["at"])
        b = {"x": px(p["evolves"]["to"]), "y": a["y"]}
        length = b["x"] - a["x"]
        stop = {"x": b["x"] - min(8, length / 2), "y": b["y"]}
        name = name_of(p)
        ink_seg("an evolution arrow", {"x1": a["x"], "y1": a["y"], "x2": stop["x"], "y2": stop["y"]})
        ink("an evolution arrow", {"x": stop["x"] - 10, "y": stop["y"] - 5, "w": 12, "h": 10})
        ink("a point", {"x": b["x"] - 7, "y": b["y"] - 7, "w": 14, "h": 14})
        p_item: dict = {"x": b["x"], "y": b["y"], "tone": "muted", "shape": "ring"}
        if p.get("reveal"):
            p_item["reveal"] = p["reveal"]
        points.append(p_item)
        l_item: dict = {"x1": a["x"], "y1": a["y"], "x2": stop["x"], "y2": stop["y"], "tone": p.get("tone") or "accent", "dashed": True, "arrow": True}
        if p.get("reveal"):
            l_item["reveal"] = p["reveal"]
        lines.append(l_item)
        dots.append({**b, "owner": i, "target": True, "name": name})
        if length < 24:
            clashes.append(f'plane: "{name}" (point {i + 1}) evolves only {js_round(length)}px to the right, too short to draw the arrow (move evolves.to further right or widen the figure)')

    def parts(i: int) -> list[dict]:
        return [d for d in dots if d["owner"] == i]

    def near(a: dict, b: dict) -> bool:
        return math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < 14

    def on_arrow(i: int, d: dict) -> bool:
        ps = parts(i)
        ring = next((q for q in ps if q["target"]), None)
        src = next((q for q in ps if not q["target"]), None)
        return bool(ring) and bool(src) and abs(d["y"] - src["y"]) < 12 and d["x"] > src["x"] + 7 and d["x"] < ring["x"] - 7

    for i in range(len(pts_list)):
        for j in range(i + 1, len(pts_list)):
            if not pts_list[i].get("evolves") and not pts_list[j].get("evolves"):
                continue
            pi, pj = parts(i), parts(j)
            if any(near(a, b) for a in pi for b in pj) or any(on_arrow(i, b) for b in pj) or any(on_arrow(j, a) for a in pi):
                def tag(k: int) -> str:
                    return f'"{name_of(pts_list[k])}" (point {k + 1})'

                clashes.append(f"plane: {tag(i)} and {tag(j)} overlap — a point, an evolution arrow or a target ring of one meets the other (move a point, or change evolves.to)")

    paths: list[dict] = []
    for pa in band.get("paths") or []:
        if len(pa["through"]) < 2:
            raise ValueError("plane(): a path needs at least 2 points in `through`")
        raw = [pt(q) for q in pa["through"]]
        kept = [i == 0 or raw[i]["x"] != raw[i - 1]["x"] or raw[i]["y"] != raw[i - 1]["y"] for i in range(len(raw))]
        pts2 = [q for i, q in enumerate(raw) if kept[i]]
        sr = pa.get("segReveal")
        seg_reveal = [sr[i - 1] for i in range(len(raw)) if i > 0 and kept[i]] if sr else None
        if len(pts2) < 2:
            raise ValueError("plane(): a path needs at least 2 different points in `through`")
        if not pa.get("smooth"):
            curves: list = []
        elif all(i == 0 or pts2[i]["x"] > pts2[i - 1]["x"] for i in range(len(pts2))):
            curves = monotone_curves(pts2)
        else:
            curves = centripetal_curves(pts2)
        samples = [pts2[0]]
        if curves:
            for i, (c1, c2, e) in enumerate(curves):
                a = pts2[i]
                n = max(8, math.ceil(math.hypot(e["x"] - a["x"], e["y"] - a["y"]) / 6))
                for k in range(1, n + 1):
                    samples.append(bez(a, c1, c2, e, k / n))
        else:
            samples.extend(pts2[1:])
        for i in range(1, len(samples)):
            ink_seg("a path", {"x1": samples[i - 1]["x"], "y1": samples[i - 1]["y"], "x2": samples[i]["x"], "y2": samples[i]["y"]})
        end = pts2[-1]
        from_ = curves[-1][1] if curves else pts2[-2]
        ux, uy = end["x"] - from_["x"], end["y"] - from_["y"]
        if math.hypot(ux, uy) < 1e-6:
            ux, uy = end["x"] - pts2[-2]["x"], end["y"] - pts2[-2]["y"]
        length = math.hypot(ux, uy) or 1
        ux, uy = ux / length, uy / length
        if pa.get("arrow"):
            xs = [end["x"], end["x"] - ux * 10 - uy * 5, end["x"] - ux * 10 + uy * 5]
            ys = [end["y"], end["y"] - uy * 10 + ux * 5, end["y"] - uy * 10 - ux * 5]
            ink("a path arrow", {"x": min(xs), "y": min(ys), "w": max(xs) - min(xs), "h": max(ys) - min(ys)})
        overshoot = max([0.0] + [max(plot_l - q["x"], q["x"] - plot_r, plot_t - q["y"], q["y"] - plot_b) for q in samples])
        item = {"pts": pts2, "curves": curves, "tone": pa.get("tone") or "accent", "dashed": pa.get("dashed") or False, "arrow": bool(pa.get("arrow")), "tip": {"dx": ux, "dy": uy}}
        if pa.get("reveal") is not None:
            item["reveal"] = pa["reveal"]
        if seg_reveal is not None:
            item["segReveal"] = seg_reveal
        item["overshoot"] = overshoot
        paths.append(item)

    dims: list[dict] = []
    for di, dm in enumerate(band.get("dims") or []):
        a = pt(dm["from"])
        b = pt(dm["to"])
        tone = dm.get("tone") or "text"
        dx_ = b["x"] - a["x"]
        dy_ = b["y"] - a["y"]
        length = math.hypot(dx_, dy_) or 1
        side = dm.get("side") or ("above" if abs(dx_) >= abs(dy_) else "right")
        nx0, ny0 = -dy_ / length, dx_ / length
        want = {"above": (0, -1), "below": (0, 1), "left": (-1, 0)}.get(side, (1, 0))
        sgn = 1 if (nx0 * want[0] + ny0 * want[1]) >= 0 else -1
        off = dm.get("offset") if dm.get("offset") is not None else DIM_OFFSET * g / 14
        ox, oy = sgn * nx0 * off, sgn * ny0 * off
        line = {"x1": a["x"] + ox, "y1": a["y"] + oy, "x2": b["x"] + ox, "y2": b["y"] + oy}
        mx, my = (line["x1"] + line["x2"]) / 2, (line["y1"] + line["y2"]) / 2
        lw = tw(dm["label"], 700)
        chip_h = g + 10
        chip = {"x": mx - lw / 2 - DIM_CHIP_PAD, "y": my - chip_h / 2, "w": lw + 2 * DIM_CHIP_PAD, "h": chip_h}
        text_item: dict = {"s": dm["label"], "x": mx, "y": my + half, "anchor": "middle", "tone": tone, "bold": True}
        if dm.get("reveal") is not None:
            text_item["reveal"] = dm["reveal"]
        texts.append(text_item)
        boxes.append({"label": dm["label"], **chip, "dim": di})
        ink_seg("a dimension line", line, di)
        ink_seg("a dimension line", {"x1": a["x"], "y1": a["y"], "x2": line["x1"], "y2": line["y1"]}, di)
        ink_seg("a dimension line", {"x1": b["x"], "y1": b["y"], "x2": line["x2"], "y2": line["y2"]}, di)
        dim_item: dict = {"from": a, "to": b, "line": line, "ext": [{"x1": a["x"], "y1": a["y"], "x2": line["x1"], "y2": line["y1"]}, {"x1": b["x"], "y1": b["y"], "x2": line["x2"], "y2": line["y2"]}], "chip": chip, "tone": tone}
        if dm.get("reveal") is not None:
            dim_item["reveal"] = dm["reveal"]
        dims.append(dim_item)

    for l in band.get("labels") or []:
        q = pt(l["at"])
        off = l.get("offset") or (0, 0)
        add_text(l["text"], q["x"] + off[0], q["y"] + half + off[1], l.get("anchor") or "middle", l.get("tone") or "text", bool(l.get("bold")), l.get("reveal"))

    def hits(b: dict, self_idx: int) -> bool:
        if b["x"] < left - 0.5 or b["x"] + b["w"] > left + width + 0.5 or b["y"] < y - 0.5 or b["y"] + b["h"] > y + h + 0.5:
            return True
        if any(overlaps(b, ob) for ob in obstacles):
            return True
        return any(overlaps(b, o) for i, o in enumerate(boxes) if i != self_idx)

    for a in auto_labels:
        if not hits(boxes[a["box"]], a["box"]):
            continue
        moved = False
        tww = tw(a["label"], 700)
        for side in sides:
            if side == a["first"]:
                continue
            sp = spot(side, a["q"])
            box_x = sp["x"] - tww / 2 if sp["anchor"] == "middle" else (sp["x"] - tww if sp["anchor"] == "end" else sp["x"])
            box = {"x": box_x, "y": sp["base"] - size, "w": tww, "h": label_h}
            if hits(box, a["box"]):
                continue
            texts[a["text"]] = {**texts[a["text"]], "x": sp["x"], "y": sp["base"], "anchor": sp["anchor"]}
            boxes[a["box"]] = {**boxes[a["box"]], **box}
            moved = True
            break
        if not moved and a["leader"]:
            x0 = plot_r + 8
            base = a["q"]["y"] + half
            tww2 = tw(a["label"], 700)
            texts[a["text"]] = {**texts[a["text"]], "x": x0, "y": base, "anchor": "start"}
            boxes[a["box"]] = {**boxes[a["box"]], "x": x0, "y": base - size, "w": tww2, "h": label_h}
            end_labels.append({"text": a["text"], "box": a["box"], "y": a["q"]["y"], "from": a["q"]})

    if len(end_labels) >= 1:
        sorted_el = sorted(end_labels, key=lambda e: e["y"])
        pitch = label_h + 2
        lo = plot_t + size - 2
        hi = plot_b - 18
        ys = [min(hi, max(lo, e["y"] + half)) for e in sorted_el]
        for i in range(1, len(ys)):
            ys[i] = max(ys[i], ys[i - 1] + pitch)
        if ys[-1] > hi:
            ys[-1] = hi
            for i in range(len(ys) - 2, -1, -1):
                ys[i] = min(ys[i], ys[i + 1] - pitch)
        ys = [v - half for v in ys]
        for i, e in enumerate(sorted_el):
            base = ys[i] + half
            texts[e["text"]] = {**texts[e["text"]], "y": base}
            boxes[e["box"]] = {**boxes[e["box"]], "y": base - size}
            if e.get("from"):
                lines.append({"x1": e["from"]["x"], "y1": e["from"]["y"], "x2": plot_r + 4, "y2": base - half, "tone": "muted", "dashed": True, "arrow": False})

    result: dict = {"type": "plane", "x": x, "y": y, "w": w, "h": h}
    if band.get("id") is not None:
        result["id"] = band["id"]
    if band.get("reveal") is not None:
        result["reveal"] = band["reveal"]
    if band.get("until") is not None:
        result["until"] = band["until"]
    result["labelSize"] = size
    result["bounds"] = {"x": left, "y": y, "w": width, "h": h}
    result["axisX"] = axis_x
    result["axisY"] = axis_y
    result["plotL"] = plot_l
    result["plotR"] = plot_r
    result["plotT"] = plot_t
    result["plotB"] = plot_b
    result["yDown"] = y_down
    result["ticks"] = ticks
    result["grid"] = grid
    result["texts"] = texts
    result["points"] = points
    result["lines"] = lines
    if paths:
        result["paths"] = paths
    result["dims"] = dims
    result["labelBoxes"] = boxes
    result["obstacles"] = obstacles
    if clashes:
        result["clashes"] = list(dict.fromkeys(clashes))
    return result


def render_plane(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:23-77 renderPlane()."""

    def col(t: str) -> str:
        return text_color_of(t, day)

    def seg(s: dict) -> str:
        return f"M{js_round(s['x1'])},{js_round(s['y1'])} L{js_round(s['x2'])},{js_round(s['y2'])}"

    def head(x: float, y: float, dx: float, dy: float, color: str) -> str:
        length = math.hypot(dx, dy) or 1
        ux, uy = dx / length, dy / length
        bigl, w = 10, 5
        pts = [(x, y), (x - ux * bigl - uy * w, y - uy * bigl + ux * w), (x - ux * bigl + uy * w, y - uy * bigl - ux * w)]
        pts_str = " ".join(f"{js_round(a)},{js_round(c)}" for a, c in pts)
        return f'<polygon points="{pts_str}" fill="{color}"/>'

    out: list[str] = []
    if b["grid"]:
        out.append(f'<path d="{" ".join(seg(s) for s in b["grid"])}" fill="none" stroke="{PALETTE["border"]}" stroke-width="2"/>')
    y_end = b["plotB"] if b["yDown"] else b["plotT"]
    x_end = b["plotR"]
    out.append(f'<path d="{seg({"x1": b["axisX"], "y1": b["axisY"], "x2": x_end, "y2": b["axisY"]})} {seg({"x1": b["axisX"], "y1": b["axisY"], "x2": b["axisX"], "y2": y_end})}" fill="none" stroke="{PALETTE["text"]}" stroke-width="2"/>')
    out.append(head(x_end, b["axisY"], 1, 0, PALETTE["text"]))
    out.append(head(b["axisX"], y_end, 0, 1 if b["yDown"] else -1, PALETTE["text"]))
    if b["ticks"]:
        out.append(f'<path d="{" ".join(seg(s) for s in b["ticks"])}" fill="none" stroke="{PALETTE["text"]}" stroke-width="2"/>')
    for l in b["lines"]:
        c = col(l["tone"])
        dash = ' stroke-dasharray="6,4"' if l.get("dashed") else ""
        out.append(f'<path d="{seg(l)}" fill="none" stroke="{c}" stroke-width="2"{dash}/>')
        if l.get("arrow"):
            out.append(head(l["x2"], l["y2"], l["x2"] - l["x1"], l["y2"] - l["y1"], c))
    for pa in b.get("paths") or []:
        c = col(pa["tone"])

        def r(q: dict) -> str:
            return f"{js_round(q['x'])},{js_round(q['y'])}"

        total = len(pa["pts"]) - 1
        k = total
        if k < 1:
            continue
        full = k >= total
        if pa["curves"]:
            d_body = " ".join(f"C{r(c1)} {r(c2)} {r(e)}" for c1, c2, e in pa["curves"][:k])
        else:
            d_body = " ".join(f"L{r(q)}" for q in pa["pts"][1 : k + 1])
        d = f"M{r(pa['pts'][0])} " + d_body
        dash = ' stroke-dasharray="6,4"' if pa.get("dashed") else ""
        out.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2"{dash}/>')
        if pa.get("arrow") and full:
            last = pa["pts"][-1]
            out.append(head(last["x"], last["y"], pa["tip"]["dx"], pa["tip"]["dy"], c))
    for dm in b["dims"]:
        c = col(dm["tone"])
        for e in dm["ext"]:
            out.append(f'<path d="{seg(e)}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="2" stroke-dasharray="2,4" stroke-linecap="round"/>')
        out.append(f'<path d="{seg(dm["line"])}" fill="none" stroke="{c}" stroke-width="2"/>')
        out.append(head(dm["line"]["x1"], dm["line"]["y1"], dm["line"]["x1"] - dm["line"]["x2"], dm["line"]["y1"] - dm["line"]["y2"], c))
        out.append(head(dm["line"]["x2"], dm["line"]["y2"], dm["line"]["x2"] - dm["line"]["x1"], dm["line"]["y2"] - dm["line"]["y1"], c))
        x0 = snap4(dm["chip"]["x"])
        out.append(f'<rect x="{x0}" y="{snap4(dm["chip"]["y"])}" width="{snap4(dm["chip"]["x"] + dm["chip"]["w"]) - x0}" height="{dm["chip"]["h"]}" rx="{js_num(dm["chip"]["h"] / 2)}" fill="{PALETTE["bg"]}"/>')
    for p in b["points"]:
        c = col(p["tone"])
        xi, yi = snap4(p["x"]), snap4(p["y"])
        shape = p["shape"]
        if shape == "ring":
            out.append(f'<circle cx="{xi}" cy="{yi}" r="6" fill="{PALETTE["bg"]}" stroke="{c}" stroke-width="2.5"/>')
        elif shape == "cross":
            out.append(f'<path d="M{xi - 6},{yi - 6} L{xi + 6},{yi + 6} M{xi - 6},{yi + 6} L{xi + 6},{yi - 6}" fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round"/>')
        elif shape in ("disc", "hole"):
            ex, ey = js_round(p["x"]), js_round(p["y"])
            fill = PALETTE["bg"] if shape == "hole" else c
            stroke = f' stroke="{c}" stroke-width="2.5"' if shape == "hole" else ""
            out.append(f'<path d="M{ex - 6},{ey} a6,6 0 1 0 12,0 a6,6 0 1 0 -12,0 Z" fill="{fill}"{stroke}/>')
        elif shape in ("square", "diamond", "triangle"):
            ex, ey = js_round(p["x"]), js_round(p["y"])
            if shape == "square":
                d = f"M{ex - 6},{ey - 6} H{ex + 6} V{ey + 6} H{ex - 6} Z"
            elif shape == "diamond":
                d = f"M{ex},{ey - 8} L{ex + 8},{ey} L{ex},{ey + 8} L{ex - 8},{ey} Z"
            else:
                d = f"M{ex},{ey - 8} L{ex + 8},{ey + 6} L{ex - 8},{ey + 6} Z"
            out.append(f'<path d="{d}" fill="{c}"/>')
        else:
            out.append(f'<circle cx="{xi}" cy="{yi}" r="6" fill="{c}"/>')
    for t in b["texts"]:
        anchor = "" if t["anchor"] == "start" else f' text-anchor="{t["anchor"]}"'
        weight = ' font-weight="700"' if t.get("bold") else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}"{anchor} font-size="{b["labelSize"]}"{weight} fill="{col(t["tone"])}">{emoji_span(t["s"])}</text>')
    return "\n  ".join(out)


def plane_band(opts: dict) -> dict:
    """lib/dsl/figures.ts:60-86 plane()."""
    for k in ("x", "y"):
        a = opts.get(k)
        if a and a.get("step") is not None and not (a["step"] > 0 and math.isfinite(a["step"])):
            raise ValueError(f"plane(): axis {k} step must be a number > 0 (got {a['step']})")
        if not a or not isinstance(a.get("max"), (int, float)):
            raise ValueError(f'plane(): "{k}" needs an axis, e.g. {{max: 100}}')
        if a["max"] <= (a.get("min") or 0):
            raise ValueError(f"plane(): axis {k} needs max > min")
        if a.get("categories") is not None:
            c = a["categories"]
            if not isinstance(c, list) or not c or any(not isinstance(s, str) or not s for s in c):
                raise ValueError(f"plane(): axis {k} categories must be a non-empty list of names, e.g. ['営業', '開発']")
            if a.get("ticks") is not None or a.get("step") is not None:
                raise ValueError(f"plane(): axis {k} takes categories or ticks / step, not both (the categories are its ticks)")
            if (a.get("min") or 0) >= 1 or a["max"] < len(c):
                raise ValueError(f"plane(): axis {k} puts its {len(c)} categories at 1..{len(c)}, so it needs min < 1 and max >= {len(c)} (use max: {len(c) + 1})")
    if opts.get("stages") is not None:
        st = opts["stages"]

        def name(q):
            return q if isinstance(q, str) else (q.get("name") if isinstance(q, dict) else None)

        if not isinstance(st, list) or len(st) < 2 or any(not isinstance(name(q), str) or not name(q) for q in st):
            raise ValueError("plane(): stages must be a list of at least 2 names (or {name, to?}), e.g. ['起源', 'カスタム', '製品', 'コモディティ']")
        if opts["x"].get("ticks") is not None or opts["x"].get("step") is not None or opts["x"].get("categories") is not None:
            raise ValueError("plane(): stages are the x axis ticks, so x takes no ticks / step / categories with them")
        tos = [None if isinstance(q, str) else q.get("to") for q in st]
        if any(t is not None for t in tos):
            min_v = opts["x"].get("min") or 0
            inner = tos[:-1]
            if tos[-1] is not None:
                raise ValueError("plane(): the last stage runs to the end of the x axis, so it takes no `to`")
            if any(not isinstance(t, (int, float)) or not math.isfinite(t) for t in inner):
                raise ValueError("plane(): when a stage says where it ends (`to`), every stage but the last must")
            for i, t in enumerate(inner):
                assert isinstance(t, (int, float))  # every element of inner was checked finite int/float above
                prev = inner[i - 1] if i else min_v
                assert isinstance(prev, (int, float))
                if t <= prev or t >= opts["x"]["max"]:
                    raise ValueError("plane(): stage `to` values must increase and stay inside the x axis")
    for p in opts.get("points") or []:
        if p.get("evolves"):
            to = p["evolves"].get("to")
            min_v = opts["x"].get("min") or 0
            if not isinstance(to, (int, float)) or not (to > p["at"][0]) or to > opts["x"]["max"] or to < min_v:
                raise ValueError(f"plane(): a point's evolves.to must be a number right of the point (x {p['at'][0]}) and inside the x axis (got {to})")
    return {"type": "plane", **opts, "height": opts.get("height") if opts.get("height") is not None else 300}
