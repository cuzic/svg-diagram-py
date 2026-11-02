"""1:1 port of lib/bars.ts's layoutBars() (exported, golden-tested live) and
lib/emit-figures.ts's renderBars(), plus the bars() DSL constructor (lib/dsl/bars.ts) —
defaults + the structural validations that affect layout, not every `check()`-style type
validation (same scope decision as flow_shapes.py's band constructors).

NOT ported: rangeBars()/pareto()/histogram()/scatter() — convenience wrappers built on
bars()/plane() that pull in lib/qc.ts/lib/qc-plane.ts (Sturges' rule, normal-curve fitting,
least-squares regression, Pareto ordering) and plane() itself (not ported). Deferred, see
BANDS.md.

Golden master: lib/bars.ts + lib/dsl/bars.ts + lib/emit-figures.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import text_width
from .charts_base import inset_or_need
from .charts_base import overlaps as _hit_rect
from .charts_base import seg_hits_rect
from .emit_common import emoji_span, js_num, js_round
from .plane import fmt, ticks_of
from .tokens import PALETTE, color_of

SERIES: dict[str, str] = {"a": "accent", "b": "text", "c": "muted"}
TICK, BAR, GAP, STACK_GAP = 6, 28, 18, 2
CUM_TICKS = [0, 20, 40, 60, 80, 100]
LINE_TONE: dict[str, str] = {"accent": "accent", "danger": "danger", "muted": "muted", "text": "text"}


def _size_of(band: dict, roles: dict) -> float:
    return roles[band.get("labelRole") or "note"]


def _bar_h(band: dict, s: float) -> float:
    return max(BAR, s + 14) if band.get("labelRole") else BAR


def _value_num(v: float, f) -> str:
    if callable(f):
        return str(f(v))
    if f == "exact" or (f is None and float(v).is_integer()):
        return js_num(v)
    if isinstance(f, (int, float)) and not isinstance(f, bool):
        return f"{v:.{int(f)}f}"
    whole = math.floor(math.log10(abs(v))) + 1 if abs(v) >= 1 else 0
    if 3 < whole <= 21:
        return js_num(_sig_round(v, whole))
    return fmt(v)


def bar_span(d: dict) -> dict:
    """lib/bars.ts:34 barSpan()."""
    if d.get("range") is not None:
        return {"lo": d["range"][0], "hi": d["range"][1]}
    return {"lo": 0, "hi": d.get("value") or 0}


def span_text(d: dict, fmt_opt, unit: str | None) -> str:
    """lib/bars.ts:36-39 spanText()."""
    span = bar_span(d)
    if d.get("range") is not None:
        return f"{_value_num(span['lo'], fmt_opt)}〜{_value_num(span['hi'], fmt_opt)}{unit or ''}"
    return f"{_value_num(span['hi'], fmt_opt)}{unit or ''}"


def _value_text(d: dict, band: dict) -> str:
    return span_text(d, band.get("valueFormat"), band.get("unit"))


def _flags(band: dict) -> dict:
    labels = band.get("labels") or "all"
    axis = band.get("axis") is not False
    return {
        "showValues": labels == "all",
        "showCats": labels != "none",
        "axis": axis,
        "grid": band.get("grid") if band.get("grid") is not None else (axis and band.get("cumulative") is None),
        "baseline": band.get("baseline") is not False,
        "labels": labels,
    }


def _segment_of(d: dict, band: dict, labels: str) -> str:
    if labels == "all":
        return f"{d['label']} {_value_text(d, band)}"
    if labels == "category":
        return d["label"]
    return ""


def _series(d: dict) -> str:
    return d.get("tone") or SERIES[d.get("series") or "a"]


def cumulative_of(data: list[dict]) -> list[float]:
    """lib/bars.ts:149-153 cumulativeOf()."""
    total = sum(bar_span(d)["hi"] for d in data)
    run = 0.0
    out = []
    for d in data:
        run += bar_span(d)["hi"]
        out.append(run / total * 100 if total > 0 else 0)
    return out


def _cum_text(pct: float) -> str:
    return f"{js_num(js_round(pct * 10) / 10)}%"


def slots_of(data: list[dict]) -> dict:
    """lib/bars.ts:174-184 slotsOf()."""
    at: dict[str, int] = {}
    slots: list[int] = []
    count = 0
    for d in data:
        slot = at.get(d["replaces"]) if d.get("replaces") is not None else None
        mine = slot if slot is not None else count
        if slot is None:
            count += 1
        slots.append(mine)
        if d.get("id"):
            at[d["id"]] = mine
    return {"slots": slots, "count": count}


def _put_text(out: dict, s: float, text: str, x: float, y: float, anchor: str, fill: str, width_of, bold: bool = False, background: str | None = None, bar: int | None = None) -> None:
    """lib/bars.ts:157-164 putText()."""
    text_obj: dict = {"text": text, "x": x, "y": y, "anchor": anchor, "fill": fill, "size": s, "bold": bold}
    if bar is not None:
        b = out["bars"][bar]
        if b.get("reveal") is not None:
            text_obj["reveal"] = b["reveal"]
        if b.get("until") is not None:
            text_obj["until"] = b["until"]
        text_obj["bar"] = bar
    out["texts"].append(text_obj)
    w = text_width(width_of, text, s, 700 if bold else 400)
    box: dict = {"label": text, "x": (x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)), "y": y - s, "w": w, "h": s + 4}
    if background is not None:
        box["background"] = background
    if bar is not None:
        box["bar"] = bar
    out["labelBoxes"].append(box)


def _add_bar(out: dict, d: dict, r: dict) -> dict:
    """lib/bars.ts:166-171 addBar()."""
    bar = dict(r)
    bar["fill"] = _series(d)
    if d.get("id") is not None:
        bar["id"] = d["id"]
    if d.get("reveal") is not None:
        bar["reveal"] = d["reveal"]
    if d.get("until") is not None:
        bar["until"] = d["until"]
    out["bars"].append(bar)
    if d.get("id"):
        out["anchors"].append({**bar, "id": d["id"]})
    return bar


def _vline_rows(band: dict, plot_l: float, plot_r: float, plot_t: float, s: float, width_of, values: list[dict]) -> dict:
    """lib/bars.ts:79-93 vlineRows()."""
    count = slots_of(band["data"])["count"]
    slot = (plot_r - plot_l) / count
    placed: list[dict] = []
    at_list: list[dict | None] = []
    for l in band.get("vlines") or []:
        if not l.get("label"):
            at_list.append(None)
            continue
        lx = plot_l + l["at"] * slot
        tw = text_width(width_of, l["label"], s, 700)
        if lx - tw / 2 < plot_l + 2:
            anchor = "start"
        elif lx + tw / 2 > plot_r - 2:
            anchor = "end"
        else:
            anchor = "middle"
        x = lx + 4 if anchor == "start" else (lx - 4 if anchor == "end" else lx)
        x1 = x if anchor == "start" else (x - tw if anchor == "end" else x - tw / 2)
        row = 0
        while any(p["row"] == row and x1 < p["x2"] + 6 and p["x1"] < x1 + tw + 6 for p in placed) or any(
            _hit_rect({"x": x1 - 6, "y": plot_t - 8 - row * (s + 4) - s, "w": tw + 12, "h": s + 4}, b) for b in values
        ):
            row += 1
        placed.append({"x1": x1, "x2": x1 + tw, "row": row})
        at_list.append({"x": x, "anchor": anchor, "row": row})
    rows = 0
    for a in at_list:
        if a is not None:
            rows = max(rows, a["row"] + 1)
    return {"rows": rows, "at": at_list}


def _vertical_values(band: dict, plot_l: float, plot_r: float, plot_t: float, plot_b: float, s: float, width_of, slots: list[int], slot: float, bw: float, y_of) -> list[dict | None]:
    """lib/bars.ts:98-133 verticalValues()."""
    cum_segs: list[dict] = []
    if band.get("cumulative") is not None:
        pts = [{"x": plot_l, "y": plot_b}]
        for k, p in enumerate(cumulative_of(band["data"])):
            pts.append({"x": plot_l + (k + 1) * slot, "y": plot_b - p / 100 * (plot_b - plot_t)})
        for k in range(len(pts) - 1):
            cum_segs.append({"x1": pts[k]["x"], "y1": pts[k]["y"], "x2": pts[k + 1]["x"], "y2": pts[k + 1]["y"]})
        guide = band["cumulative"].get("guide")
        if guide is not None:
            gy = plot_b - guide / 100 * (plot_b - plot_t)
            cum_segs.append({"x1": plot_l, "y1": gy, "x2": plot_r, "y2": gy})
    for l in band.get("lines") or []:
        cum_segs.append({"x1": plot_l, "y1": y_of(l["at"]), "x2": plot_r, "y2": y_of(l["at"])})
    vx = [plot_l + l["at"] * slot for l in (band.get("vlines") or [])]

    def dodge(cx: float, tw: float, lo: float, hi: float) -> float:
        def cuts(c: float) -> bool:
            return any(v > c - tw / 2 - 3 and v < c + tw / 2 + 3 for v in vx)

        if not cuts(cx):
            return cx
        sides = [c for v in vx for c in (v - 3.5 - tw / 2, v + 3.5 + tw / 2) if not cuts(c)]

        def near(cs: list[float]) -> float | None:
            if not cs:
                return None
            best = cs[0]
            for c in cs[1:]:
                if abs(c - cx) < abs(best - cx):
                    best = c
            return best

        r = near([c for c in sides if c - tw / 2 >= lo + 1 and c + tw / 2 <= hi - 1])
        if r is not None:
            return r
        r = near([c for c in sides if c - tw / 2 >= lo - tw and c + tw / 2 <= hi + tw])
        return r if r is not None else cx

    out: list[dict | None] = []
    for i, d in enumerate(band["data"]):
        span = bar_span(d)
        lo, hi = span["lo"], span["hi"]
        if band.get("hideZero") and hi == 0:
            out.append(None)
            continue
        bh = (hi - lo) / band["max"] * (plot_b - plot_t)
        bx = plot_l + slots[i] * slot + (slot - bw) / 2
        r_y = plot_b - hi / band["max"] * (plot_b - plot_t)
        tw = text_width(width_of, _value_text(d, band), s, 700)
        cx = dodge(bx + bw / 2, tw, bx, bx + bw)
        cx_out = dodge(bx + bw / 2, tw, plot_l + slots[i] * slot, plot_l + (slots[i] + 1) * slot)

        def cut(at: float, base: float) -> bool:
            return any(seg_hits_rect(sg, {"x": at - tw / 2, "y": base - s + 2, "w": tw, "h": s}) for sg in cum_segs)

        def fits_in(base: float) -> bool:
            return bw >= tw + 12 and base - s >= r_y and base <= r_y + bh and cx - tw / 2 >= bx - 0.5 and cx + tw / 2 <= bx + bw + 0.5

        places = []
        if bh >= s + 10:
            places.append({"base": r_y + s + 4, "inside": True})
        places.append({"base": r_y - 6, "inside": False})
        if bh >= 2 * s + 14:
            places.append({"base": r_y + bh - 8, "inside": True})
        places.append({"base": r_y - 6 - s - 6, "inside": False})
        if bh < s + 10 and cum_segs:
            places.append({"base": r_y + s + 2, "inside": True})
        ok = [p for p in places if not p["inside"] or fits_in(p["base"])]
        pick = None
        if cum_segs:
            pick = next((p for p in ok if not cut(cx if p["inside"] else cx_out, p["base"])), None)
        if pick is None:
            pick = ok[0] if ok else places[1]
        at = cx if pick["inside"] else cx_out
        out.append({"cx": at, "base": pick["base"], "inside": pick["inside"], "box": {"x": at - tw / 2, "y": pick["base"] - s, "w": tw, "h": s + 4}})
    return out


def layout_bars(band: dict, x: float, y: float, w: float, width_of, roles: dict) -> dict:
    """lib/bars.ts:186-188 layoutBars()."""
    if band.get("dir") == "v":
        return _layout_vertical(band, x, y, w, width_of, roles)
    return _layout_horizontal(band, x, y, w, width_of, roles)


def _layout_horizontal(band: dict, x: float, y: float, w: float, width_of, roles: dict) -> dict:
    """lib/bars.ts:190-244 layoutHorizontal()."""
    f = _flags(band)
    s = _size_of(band, roles)
    barh = _bar_h(band, s)
    slots_info = slots_of(band["data"])
    slots, count = slots_info["slots"], slots_info["count"]
    rows = 1 if band.get("stack") else count
    bh = barh if band.get("barRatio") is None or band.get("stack") else (barh + GAP) * band["barRatio"]
    gp = GAP if band.get("barRatio") is None or band.get("stack") else barh + GAP - bh
    tick_h = s + TICK + 8 if f["axis"] else 0
    ticks = ticks_of({"max": band["max"]}, "bars") if f["axis"] else []
    label_w = 0 if band.get("stack") or not f["showCats"] else max(text_width(width_of, d["label"], s, 400) for d in band["data"]) + 12
    value_w = 0 if band.get("stack") or not f["showValues"] else max(text_width(width_of, _value_text(d, band), s, 700) for d in band["data"]) + 12
    tick_pad_l = text_width(width_of, ticks[0]["label"], s, 400) / 2 if band.get("stack") and f["axis"] else 0
    tick_pad_r = text_width(width_of, ticks[-1]["label"], s, 400) / 2 if band.get("stack") and f["axis"] else 0
    inset_l, inset_r = inset_or_need("bars()", band.get("plotInset"), label_w + tick_pad_l, value_w + tick_pad_r)
    plot_l, plot_r = x + inset_l, x + w - inset_r
    plot_w = plot_r - plot_l
    if plot_w < (80 if (f["axis"] or f["labels"] != "none") else 20):
        raise ValueError("bars(): the figure is too narrow for its labels")
    segs = [_segment_of(d, band, f["labels"]) for d in band["data"]]
    has_outside = bool(band.get("stack")) and any(segs[i] and bar_span(d)["hi"] / band["max"] * plot_w < text_width(width_of, segs[i], s, 700) + 12 for i, d in enumerate(band["data"]))
    outside_h = s + 6 if has_outside else 0
    need_h = rows * bh + max(0, rows - 1) * gp + (tick_h + 8 if f["axis"] else 0) + outside_h
    if band.get("height") is not None and band["height"] < need_h:
        raise ValueError(f"bars(): height {band['height']} is too small for its content (need at least {need_h})")
    h = band.get("height") if band.get("height") is not None else need_h
    out: dict = {"type": "bars", "x": x, "y": y, "w": w, "h": h, "dir": "h", "stack": bool(band.get("stack")), "bars": [], "ticks": [], "texts": [], "labelBoxes": [], "anchors": []}
    if band.get("id") is not None:
        out["id"] = band["id"]
    if band.get("reveal") is not None:
        out["reveal"] = band["reveal"]
    if band.get("until") is not None:
        out["until"] = band["until"]
    axis_y = y + rows * bh + max(0, rows - 1) * gp
    for t in ticks:
        tx = plot_l + t["at"] / band["max"] * plot_w
        if f["grid"] and (f["baseline"] or t["at"] != 0):
            out["ticks"].append({"x1": tx, "y1": y, "x2": tx, "y2": axis_y + TICK})
        else:
            out["ticks"].append({"x1": tx, "y1": axis_y, "x2": tx, "y2": axis_y + TICK})
        _put_text(out, s, t["label"], tx, axis_y + outside_h + TICK + s + 2, "middle", "muted", width_of)
    if f["baseline"] and not (f["axis"] and f["grid"]):
        out["ticks"].append({"x1": plot_l, "y1": y, "x2": plot_l, "y2": axis_y})
    if band.get("stack"):
        at = plot_l
        for i, d in enumerate(band["data"]):
            raw_w = bar_span(d)["hi"] / band["max"] * plot_w
            bw = max(0, raw_w - (STACK_GAP if i < len(band["data"]) - 1 else 0))
            r = _add_bar(out, d, {"x": at, "y": y, "w": bw, "h": barh})
            bar = len(out["bars"]) - 1
            text = segs[i]
            tw = text_width(width_of, text, s, 700)
            if text and bw >= tw + 12:
                _put_text(out, s, text, r["x"] + r["w"] / 2, r["y"] + barh / 2 + s * 0.36, "middle", "bg", width_of, True, r["fill"], bar)
            elif text:
                _put_text(out, s, text, r["x"] + r["w"] / 2, r["y"] + barh + s + 4, "middle", r["fill"], width_of, True, None, bar)
            at += raw_w
    else:
        for i, d in enumerate(band["data"]):
            span = bar_span(d)
            lo, hi = span["lo"], span["hi"]
            by = y + slots[i] * (bh + gp)
            x0 = plot_l + lo / band["max"] * plot_w
            bw = (hi - lo) / band["max"] * plot_w
            r = _add_bar(out, d, {"x": x0, "y": by, "w": bw, "h": bh})
            bar = len(out["bars"]) - 1
            if f["showCats"]:
                _put_text(out, s, d["label"], plot_l - 8, by + bh / 2 + s * 0.36, "end", "text", width_of, False, None, bar)
            if not f["showValues"]:
                continue
            text = _value_text(d, band)
            tw = text_width(width_of, text, s, 700)
            if bw >= tw + 12:
                _put_text(out, s, text, x0 + bw - 6, by + bh / 2 + s * 0.36, "end", "bg", width_of, True, r["fill"], bar)
            else:
                _put_text(out, s, text, x0 + bw + 6, by + bh / 2 + s * 0.36, "start", r["fill"], width_of, True, None, bar)
    if f["axis"]:
        out["ticks"].append({"x1": plot_l, "y1": axis_y, "x2": plot_r, "y2": axis_y})
    return out


def _layout_vertical(band: dict, x: float, y: float, w: float, width_of, roles: dict) -> dict:
    """lib/bars.ts:246-317 layoutVertical()."""
    f = _flags(band)
    s = _size_of(band, roles)
    h = band.get("height") if band.get("height") is not None else 280
    ticks = ticks_of({"max": band["max"]}, "bars") if f["axis"] else []
    if f["axis"] and band.get("cumulative") is not None and band["max"] - ticks[-1]["at"] > band["max"] * 0.08:
        ticks.append({"at": band["max"], "label": fmt(band["max"])})
    tick_w = max([0.0] + [text_width(width_of, t["label"], s, 400) for t in ticks])
    cum_w = (max(text_width(width_of, f"{p}%", s, 400) for p in CUM_TICKS) + TICK + 10) if band.get("cumulative") is not None else 0

    def edge_half(i: int) -> float:
        edges = band.get("edges")
        if not edges:
            return 0
        idx = i
        return text_width(width_of, edges[idx] if 0 <= idx < len(edges) else "", s, 400) / 2

    edges = band.get("edges")
    plot_l = max(x + (tick_w + TICK + 10 if f["axis"] else 4), x + edge_half(0))
    plot_r = min(x + w - (cum_w if band.get("cumulative") is not None else 8), x + w - edge_half(len(edges) - 1 if edges else 0) - 2)
    slots_info = slots_of(band["data"])
    slots, count = slots_info["slots"], slots_info["count"]
    slot = (plot_r - plot_l) / count
    bw = min(64, slot * 0.62) if band.get("barRatio") is None else slot * band["barRatio"]
    top_labels = any(l.get("label") for l in [*(band.get("lines") or []), *(band.get("vlines") or [])])
    plot_b = y + h - s * 1.4 - 14 if f["showCats"] or band.get("edges") else y + h - 4

    def plot_t_of(rows: int) -> float:
        return y + (s + 8 if (f["axis"] or f["showValues"] or top_labels or band.get("cumulative") is not None) else 4) + max(0, rows - 1) * (s + 4)

    def rows_at(rows: int) -> dict:
        plot_t = plot_t_of(rows)

        def y_of(v: float) -> float:
            return plot_b - v / band["max"] * (plot_b - plot_t)

        values = (
            [p["box"] for p in _vertical_values(band, plot_l, plot_r, plot_t, plot_b, s, width_of, slots, slot, bw, y_of) if p]
            if f["showValues"] and not band.get("stack")
            else []
        )
        return _vline_rows(band, plot_l, plot_r, plot_t, s, width_of, values)

    rows = _vline_rows(band, plot_l, plot_r, plot_t_of(0), s, width_of, [])["rows"]
    vrows = rows_at(rows)
    most = max(rows, vrows["rows"])
    n = 0
    while n < 3 and vrows["rows"] != rows:
        rows = vrows["rows"]
        vrows = rows_at(rows)
        most = max(most, vrows["rows"])
        n += 1
    if vrows["rows"] != rows:
        rows = most
        vrows = rows_at(rows)
        while vrows["rows"] > rows:
            rows = vrows["rows"]
            vrows = rows_at(rows)
    plot_t = plot_t_of(rows)
    if plot_r - plot_l < (80 if (f["axis"] or f["labels"] != "none") else 20) or plot_b - plot_t < (80 if (f["axis"] or f["showValues"]) else 20):
        raise ValueError("bars(): the figure is too small; raise width / height")
    out: dict = {"type": "bars", "x": x, "y": y, "w": w, "h": h, "dir": "v", "stack": bool(band.get("stack")), "bars": [], "ticks": [], "texts": [], "labelBoxes": [], "anchors": []}
    if band.get("id") is not None:
        out["id"] = band["id"]
    if band.get("reveal") is not None:
        out["reveal"] = band["reveal"]
    if band.get("until") is not None:
        out["until"] = band["until"]

    def y_of(v: float) -> float:
        return plot_b - v / band["max"] * (plot_b - plot_t)

    for t in ticks:
        ty = y_of(t["at"])
        if f["grid"] and (f["baseline"] or t["at"] != 0):
            out["ticks"].append({"x1": plot_l - TICK, "y1": ty, "x2": plot_r, "y2": ty})
        else:
            out["ticks"].append({"x1": plot_l - TICK, "y1": ty, "x2": plot_l, "y2": ty})
        _put_text(out, s, t["label"], plot_l - TICK - 4, ty + (s * 5 / 14 if band.get("labelRole") else 5), "end", "muted", width_of)
    if band.get("stack"):
        bw2 = min(72, (plot_r - plot_l) * 0.35)
        bx = (plot_l + plot_r - bw2) / 2
        bottom = plot_b
        for i, d in enumerate(band["data"]):
            raw_h = bar_span(d)["hi"] / band["max"] * (plot_b - plot_t)
            bh = max(0, raw_h - (STACK_GAP if i > 0 else 0))
            r = {"x": bx, "y": bottom - raw_h, "w": bw2, "h": bh}
            _add_bar(out, d, r)
            bar = len(out["bars"]) - 1
            text = _segment_of(d, band, f["labels"])
            tw = text_width(width_of, text, s, 700)
            if text and bh >= s + 10 and bw2 >= tw + 12:
                _put_text(out, s, text, bx + bw2 / 2, r["y"] + bh / 2 + s * 0.36, "middle", "bg", width_of, True, out["bars"][bar]["fill"], bar)
            elif text:
                _put_text(out, s, text, bx + bw2 + 8, r["y"] + bh / 2 + s * 0.36, "start", out["bars"][bar]["fill"], width_of, True, None, bar)
            bottom -= raw_h
    else:
        values = _vertical_values(band, plot_l, plot_r, plot_t, plot_b, s, width_of, slots, slot, bw, y_of) if f["showValues"] else []
        for i, d in enumerate(band["data"]):
            span = bar_span(d)
            lo, hi = span["lo"], span["hi"]
            bh = (hi - lo) / band["max"] * (plot_b - plot_t)
            bx = plot_l + slots[i] * slot + (slot - bw) / 2
            r = _add_bar(out, d, {"x": bx, "y": plot_b - hi / band["max"] * (plot_b - plot_t), "w": bw, "h": bh})
            bar = len(out["bars"]) - 1
            if f["showCats"] and not band.get("edges"):
                _put_text(out, s, d["label"], bx + bw / 2, plot_b + s + 10, "middle", "text", width_of, False, None, bar)
            pick = values[i] if i < len(values) else None
            if not pick:
                continue
            text = _value_text(d, band)
            if pick["inside"]:
                _put_text(out, s, text, pick["cx"], pick["base"], "middle", "bg", width_of, True, r["fill"], bar)
            else:
                _put_text(out, s, text, pick["cx"], pick["base"], "middle", r["fill"], width_of, True, None, bar)
    if f["axis"]:
        out["ticks"].append({"x1": plot_l, "y1": plot_t, "x2": plot_l, "y2": plot_b})
    if f["baseline"]:
        out["ticks"].append({"x1": plot_l, "y1": plot_b, "x2": plot_r, "y2": plot_b})
    _overlays(out, band, {"plotL": plot_l, "plotR": plot_r, "plotT": plot_t, "plotB": plot_b, "S": s, "widthOf": width_of, "yOf": y_of, "vrows": vrows})
    return out


def _overlays(out: dict, band: dict, g: dict) -> None:
    """lib/bars.ts:320-368 overlays()."""
    plot_l, plot_r, plot_t, plot_b, s, width_of, y_of, vrows = g["plotL"], g["plotR"], g["plotT"], g["plotB"], g["S"], g["widthOf"], g["yOf"], g["vrows"]
    ink: dict = {"lines": [], "polylines": [], "dots": []}
    count = slots_of(band["data"])["count"]
    slot = (plot_r - plot_l) / count

    def x_of(at: float) -> float:
        return plot_l + at * slot

    hy: list[float] = []
    for l in sorted(band.get("lines") or [], key=lambda l: -l["at"]):
        ly = y_of(l["at"])
        fill = LINE_TONE[l.get("tone") or "danger"]
        ink["lines"].append({"x1": plot_l, "y1": ly, "x2": plot_r, "y2": ly, "fill": fill, "dashed": l.get("dashed") is not False})
        if not l.get("label"):
            continue
        near = sum(1 for y in hy if abs(y - ly) < s + 6)
        hy.append(ly)
        if near % 2 == 0:
            _put_text(out, s, l["label"], plot_r - 4, ly - 5, "end", fill, width_of, True)
        else:
            _put_text(out, s, l["label"], plot_l + 4, ly - 5, "start", fill, width_of, True)
    for i, l in enumerate(band.get("vlines") or []):
        lx = x_of(l["at"])
        fill = LINE_TONE[l.get("tone") or "danger"]
        at = vrows["at"][i]
        ink["lines"].append({"x1": lx, "y1": plot_t - 4, "x2": lx, "y2": plot_b, "fill": fill, "dashed": l.get("dashed") is not False})
        if at and at["row"] > 0:
            ink["lines"].append({"x1": lx, "y1": plot_t - 4 - at["row"] * (s + 4), "x2": lx, "y2": plot_t - 4, "fill": fill, "dashed": l.get("dashed") is not False, "soft": True})
        if l.get("label") and at:
            _put_text(out, s, l["label"], at["x"], plot_t - 8 - at["row"] * (s + 4), at["anchor"], fill, width_of, True)
    if band.get("edges"):
        for i, e in enumerate(band["edges"]):
            if e:
                _put_text(out, s, e, x_of(i), plot_b + s + 10, "middle", "text", width_of)
    if band.get("curve"):
        curve = band["curve"]
        ink["polylines"].append({"pts": [{"x": x_of(sx), "y": y_of(v)} for sx, v in curve["through"]], "fill": LINE_TONE[curve.get("tone") or "text"], "dashed": curve.get("dashed") is True, "soft": True})
    if band.get("cumulative") is not None:
        cum = cumulative_of(band["data"])

        def y_pct(p: float) -> float:
            return plot_b - p / 100 * (plot_b - plot_t)

        ink["lines"].append({"x1": plot_r, "y1": plot_t, "x2": plot_r, "y2": plot_b, "fill": "border", "dashed": False})
        for p in CUM_TICKS:
            ink["lines"].append({"x1": plot_r, "y1": y_pct(p), "x2": plot_r + TICK, "y2": y_pct(p), "fill": "border", "dashed": False})
            _put_text(out, s, f"{p}%", plot_r + TICK + 4, y_pct(p) + (s * 5 / 14 if band.get("labelRole") else 5), "start", "muted", width_of)
        guide = band["cumulative"].get("guide")
        if guide is not None:
            ink["lines"].append({"x1": plot_l, "y1": y_pct(guide), "x2": plot_r, "y2": y_pct(guide), "fill": "muted", "dashed": True})
        pts = [{"x": plot_l, "y": plot_b}] + [{"x": x_of(i + 1), "y": y_pct(p)} for i, p in enumerate(cum)]
        ink["polylines"].append({"pts": pts, "fill": "danger", "dashed": False})
        segs = [l for l in ink["lines"] if not l.get("soft")] + [{"x1": l["pts"][k]["x"], "y1": l["pts"][k]["y"], "x2": l["pts"][k + 1]["x"], "y2": l["pts"][k + 1]["y"]} for l in ink["polylines"] if not l.get("soft") for k in range(len(l["pts"]) - 1)]
        for i, p in enumerate(pts[1:]):
            ink["dots"].append({"x": p["x"], "y": p["y"], "fill": "danger"})
            text = _cum_text(cum[i])
            tw = text_width(width_of, text, s, 700)
            places = [("end", p["x"] - 6, p["y"] - 7), ("middle", p["x"], p["y"] - 12), ("start", p["x"] + 6, p["y"] - 7), ("end", p["x"] - 6, p["y"] + s + 4), ("start", p["x"] + 6, p["y"] + s + 4)]

            def box_of(a: str, lx: float, ly: float) -> dict:
                return {"x": (lx - tw / 2 if a == "middle" else (lx - tw if a == "end" else lx)), "y": ly - s, "w": tw, "h": s + 4}

            def clear(b: dict) -> bool:
                return (
                    b["x"] >= out["x"]
                    and b["x"] + b["w"] <= out["x"] + out["w"]
                    and b["y"] >= out["y"]
                    and not any(_hit_rect(b, o) for o in out["labelBoxes"])
                    and not any(seg_hits_rect(sg, b) for sg in segs)
                )

            at = next((pl for pl in places if clear(box_of(*pl))), places[0])
            _put_text(out, s, text, at[1], at[2], at[0], "danger", width_of, True)
    if ink["lines"] or ink["polylines"] or ink["dots"]:
        out["ink"] = ink


# ---------------------------------------------------------------------------------------------------------------------------
# lib/dsl/bars.ts's bars() constructor
# ---------------------------------------------------------------------------------------------------------------------------


def bars_band(data: list[dict], *, unit: str | None = None, direction: str | None = None, stack: bool = False, height: float | None = None, id: str | None = None, max_value: float | None = None, plot_inset: tuple[float, float] | None = None, labels: str | None = None, axis: bool | None = None, grid: bool | None = None, baseline: bool | None = None, bar_ratio: float | None = None, label_role: str | None = None, hide_zero: bool = False, lines: list[dict] | None = None, vlines: list[dict] | None = None, curve: dict | None = None, cumulative: dict | None = None, edges: list[str] | None = None, value_format=None) -> dict:
    """lib/dsl/bars.ts:43-92 bars(). `direction` is Node's `dir` ('h'/'v'); `max_value` is
    Node's `max` — both renamed here to avoid shadowing the `dir`/`max` builtins this function
    calls (the band dict's keys are still Node's own "dir"/"max")."""
    if not data:
        raise ValueError("bars(data) needs at least one value")
    for d in data:
        if (d.get("value") is None) == (d.get("range") is None):
            raise ValueError(f"bars(): \"{d['label']}\" needs exactly one of value and range")
        if d.get("range") is not None:
            lo, hi = d["range"]
            if lo < 0:
                raise ValueError(f"bars(): range for \"{d['label']}\" starts below 0 ({lo}); the axis of bars() starts at 0")
            if not (lo < hi):
                raise ValueError(f"bars(): range for \"{d['label']}\" needs lo < hi (got [{lo}, {hi}]); a single value is a plain bar")
        else:
            if d.get("value", 0) < 0:
                raise ValueError(f"bars(): value for \"{d['label']}\" must be >= 0 (got {d.get('value')})")
    extent = sum(bar_span(d)["hi"] for d in data) if stack else max(bar_span(d)["hi"] for d in data)
    m = max_value if max_value is not None else extent
    if not (m > 0):
        raise ValueError(f"bars(): max must be a finite number > 0 (got {m})")
    if extent > m:
        raise ValueError(f"bars(): {'stack total' if stack else 'a value'} ({extent}) exceeds max ({m})")
    band: dict = {"type": "bars", "data": list(data), "max": m, "dir": direction or "h", "stack": stack}
    if unit is not None:
        band["unit"] = unit
    if height is not None:
        band["height"] = height
    if id is not None:
        band["id"] = id
    for k, v in (
        ("plotInset", plot_inset), ("labels", labels), ("axis", axis), ("grid", grid), ("baseline", baseline),
        ("barRatio", bar_ratio), ("labelRole", label_role), ("lines", lines), ("vlines", vlines), ("curve", curve),
        ("cumulative", cumulative), ("edges", edges), ("valueFormat", value_format),
    ):
        if v is not None:
            band[k] = v
    if hide_zero:
        band["hideZero"] = True
    return band


# ---------------------------------------------------------------------------------------------------------------------------
# lib/emit-figures.ts's renderBars() (spotlight dim/stage filtering not ported — this port's
# bands never set `dim`/`reveal` stages, so every bar/text is always visible, same scope
# decision as flow_shapes.py's render_flow_shape())
# ---------------------------------------------------------------------------------------------------------------------------


def render_bars(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:80-105 renderBars()."""
    out: list[str] = []
    for t in b["ticks"]:
        out.append(f'<path d="M{js_round(t["x1"])},{js_round(t["y1"])} L{js_round(t["x2"])},{js_round(t["y2"])}" fill="none" stroke="{PALETTE["border"]}" stroke-width="2"/>')
    for r in b["bars"]:
        x, y = js_round(r["x"] * 100) / 100, js_round(r["y"] * 100) / 100
        right, bottom = js_round((r["x"] + r["w"]) * 100) / 100, js_round((r["y"] + r["h"]) * 100) / 100
        out.append(f'<path d="M{js_num(x)},{js_num(y)} H{js_num(right)} V{js_num(bottom)} H{js_num(x)} Z" fill="{color_of(r["fill"], day)}"/>')
    ink = b.get("ink") or {}
    for l in ink.get("lines", []):
        dash = ' stroke-dasharray="6,4"' if l.get("dashed") else ""
        out.append(f'<path d="M{js_round(l["x1"])},{js_round(l["y1"])} L{js_round(l["x2"])},{js_round(l["y2"])}" fill="none" stroke="{color_of(l["fill"], day)}" stroke-width="2"{dash}/>')
    for l in ink.get("polylines", []):
        pts = " L".join(f'{js_num(js_round(p["x"] * 10) / 10)},{js_num(js_round(p["y"] * 10) / 10)}' for p in l["pts"])
        dash = ' stroke-dasharray="6,4"' if l.get("dashed") else ""
        out.append(f'<path d="M{pts}" fill="none" stroke="{color_of(l["fill"], day)}" stroke-width="2.5" stroke-linejoin="round"{dash}/>')
    for d in ink.get("dots", []):
        x, y = js_round(d["x"] * 10) / 10, js_round(d["y"] * 10) / 10
        out.append(f'<path d="M{js_num(x - 4)},{js_num(y)} a4,4 0 1 0 8,0 a4,4 0 1 0 -8,0 Z" fill="{PALETTE["bg"]}" stroke="{color_of(d["fill"], day)}" stroke-width="2.5"/>')
    for t in b["texts"]:
        anchor = "" if t["anchor"] == "start" else f' text-anchor="{t["anchor"]}"'
        weight = ' font-weight="700"' if t.get("bold") else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}"{anchor} font-size="{t["size"]}"{weight} fill="{color_of(t["fill"], day)}">{emoji_span(t["text"])}</text>')
    return "\n  ".join(out)
