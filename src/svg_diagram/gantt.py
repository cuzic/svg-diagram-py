"""1:1 port of lib/gantt.ts's layoutGantt (exported, golden-tested live) and
lib/emit-figures.ts's renderGantt.

Golden master: lib/gantt.ts + lib/emit-figures.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import datetime
import math
import re

from .atoms import text_width
from .emit_common import emoji_span, js_round, snap4
from .timeline import timeline_day, ticks_of
from .tokens import PALETTE

ROW_H, BAR_H, HEAD_H, PAD, LABEL_MAX, ARROW = 32, 18, 44, 8, 0.4, 8
SHORT_AXIS = 140
_EPOCH = datetime.date(1970, 1, 1)


def _simplify_pts(pts: list[dict]) -> list[dict]:
    """lib/gantt.ts:14-18 simplifyPts()."""
    out: list[dict] = []
    for p in pts:
        if not out or abs(out[-1]["x"] - p["x"]) > 0.01 or abs(out[-1]["y"] - p["y"]) > 0.01:
            out.append(p)
    kept = []
    for i, p in enumerate(out):
        if i == 0 or i == len(out) - 1:
            kept.append(p)
            continue
        prev, nxt = out[i - 1], out[i + 1]
        if (prev["x"] == p["x"] and p["x"] == nxt["x"]) or (prev["y"] == p["y"] and p["y"] == nxt["y"]):
            continue
        kept.append(p)
    return kept


def _is_section(r: dict) -> bool:
    return "section" in r


def _tasks_of(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not _is_section(r)]


def _fmt_day(day: float) -> str:
    d = _EPOCH + datetime.timedelta(days=day)
    return f"{d.month}/{d.day}"


def _ymd(day: float) -> str:
    d = _EPOCH + datetime.timedelta(days=day)
    return d.isoformat()


def _day_of(v: str, what: str) -> float:
    if v == "auto" and what == "today":
        raise ValueError(f"gantt(): {what}: 'auto' needs a date from the build (--today YYYY-MM-DD, SVG_DIAGRAM_TODAY or .svg-diagram.json \"today\"); it was not given one here")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)):
        raise ValueError(f"gantt(): {what} must be 'YYYY-MM-DD' (got {v!r})")
    try:
        return timeline_day(v, what)
    except ValueError:
        raise ValueError(f"gantt(): {what} is not a real date ({v})") from None


def span_of(t: dict) -> tuple[float, float]:
    """lib/gantt.ts:31-46 spanOf()."""
    s = _day_of(t["start"], f'"{t["label"]}" start')
    if t.get("milestone"):
        if t.get("end") is not None or t.get("days") is not None:
            raise ValueError(f'gantt(): "{t["label"]}" is a milestone (one day): drop end / days')
        return s, s + 1
    if t.get("end") is not None and t.get("days") is not None:
        raise ValueError(f'gantt(): "{t["label"]}" has both end and days; use one')
    if t.get("days") is not None:
        days = t["days"]
        if not (isinstance(days, int) and days >= 1):
            raise ValueError(f'gantt(): "{t["label"]}" days must be a whole number >= 1 (got {days})')
        return s, s + days
    if t.get("end") is None:
        raise ValueError(f'gantt(): "{t["label"]}" needs end or days (or milestone: true)')
    e = _day_of(t["end"], f'"{t["label"]}" end')
    if e < s:
        raise ValueError(f'gantt(): "{t["label"]}" ends ({t["end"]}) before it starts ({t["start"]})')
    return s, e + 1


def _axis_of(band: dict, spans: list[tuple[float, float]]) -> tuple[float, float]:
    """lib/gantt.ts:49-59 axisOf()."""
    from_ = _day_of(band["from"], "from") if band.get("from") is not None else min(s[0] for s in spans)
    to = _day_of(band["to"], "to") + 1 if band.get("to") is not None else max(s[1] for s in spans)
    if band.get("extendToToday") and band.get("today") is not None:
        today = _day_of(band["today"], "today")
        if band.get("from") is None and today < from_:
            from_ = today
        if band.get("to") is None and today >= to:
            to = today + 1
    return from_, to


def _mondays(from_: float, to: float) -> list[float]:
    """lib/gantt.ts:63-67 mondays()."""
    start_dow = (_EPOCH + datetime.timedelta(days=from_)).isoweekday() % 7  # JS getUTCDay(): Sun=0..Sat=6
    out = []
    d = from_ + (8 - start_dow) % 7
    while d < to:
        out.append(d)
        d += 7
    return out


def layout_gantt(*, rows: list[dict], x: float, y: float, w: float, width_of, roles: dict, from_: str | None = None, to: str | None = None, today: str | None = None, today_label: str | None = None, extend_to_today: bool = False) -> dict:
    """lib/gantt.ts:82-194 layoutGantt()."""
    s = roles["note"]
    tasks = _tasks_of(rows)
    if not tasks:
        raise ValueError("gantt(rows) needs at least one task")
    ids: dict[str, dict] = {}
    for t in tasks:
        if not isinstance(t.get("label"), str) or not t["label"].strip():
            raise ValueError("gantt(): every task needs a label")
        if t.get("progress") is not None and not (0 <= t["progress"] <= 1):
            raise ValueError(f'gantt(): "{t["label"]}" progress must be between 0 and 1 (got {t["progress"]})')
        if t.get("id") is not None:
            if t["id"] in ids:
                raise ValueError(f'gantt(): duplicate task id "{t["id"]}"')
            ids[t["id"]] = t

    spans = {id(t): span_of(t) for t in tasks}

    def afters(t: dict) -> list[str]:
        a = t.get("after")
        if a is None:
            return []
        return a if isinstance(a, list) else [a]

    for t in tasks:
        for a in afters(t):
            if a not in ids:
                raise ValueError(f'gantt(): "{t["label"]}" is after unknown task id "{a}"')
            if ids[a] is t:
                raise ValueError(f'gantt(): "{t["label"]}" is after itself')

    visiting: set[int] = set()
    done: set[int] = set()

    def visit(t: dict) -> None:
        if id(t) in done:
            return
        if id(t) in visiting:
            raise ValueError(f'gantt(): "{t["label"]}" is part of a cycle of after (a task cannot wait for itself)')
        visiting.add(id(t))
        for a in afters(t):
            visit(ids[a])
        visiting.discard(id(t))
        done.add(id(t))

    for t in tasks:
        visit(t)

    band = {"from": from_, "to": to, "today": today, "extendToToday": extend_to_today}
    axis_from, axis_to = _axis_of(band, list(spans.values()))
    if not axis_from < axis_to:
        raise ValueError("gantt(): from must be before to")
    for t in tasks:
        sp, ep = spans[id(t)]
        if sp < axis_from or ep > axis_to:
            end_part = f' - {t["end"]}' if t.get("end") else ""
            raise ValueError(f'gantt(): "{t["label"]}" ({t["start"]}{end_part}) is outside the axis (from / to)')
    today_day = _day_of(today, "today") if today is not None else None
    if today_day is not None and (today_day < axis_from or today_day >= axis_to):
        raise ValueError(f'gantt(): today ({today}) is outside the axis ({_ymd(axis_from)} - {_ymd(axis_to - 1)}): move today into it, set from / to, or pass extendToToday: true')

    label_w = max(math.ceil(text_width(width_of, (r["section"] if _is_section(r) else r["label"]), s, 700 if _is_section(r) else 400)) for r in rows) + 2 * PAD
    max_label = math.floor(w * LABEL_MAX)
    if label_w > max_label:
        raise ValueError(f"gantt(): the longest row label needs {label_w}px but only {max_label}px of the {round(w)}px figure is for labels (shorten it)")
    plot_l, plot_r = x + label_w + PAD, x + w - PAD - 12
    if plot_r - plot_l < 240:
        raise ValueError("gantt(): the chart area is too narrow (240px at least)")

    def px(day: float) -> float:
        return plot_l + (day - axis_from) / (axis_to - axis_from) * (plot_r - plot_l)

    top = y + HEAD_H
    height = HEAD_H + len(rows) * ROW_H + PAD
    out = {"x": x, "y": y, "w": w, "h": height, "plot": {"x1": plot_l, "x2": plot_r, "y1": top, "y2": y + height - PAD}, "ticks": [], "sections": [], "bars": [], "deps": [], "texts": [], "anchors": [], "labelBoxes": []}

    def text(txt: str, tx: float, ty: float, anchor: str, bold: bool = False, muted: bool = False, tone: str | None = None) -> None:
        entry = {"text": txt, "x": tx, "y": ty, "size": s, "bold": bold, "muted": muted, "anchor": anchor}
        if tone:
            entry["tone"] = tone
        out["texts"].append(entry)
        tw = text_width(width_of, txt, s, 700 if bold else 400)
        lx = tx - tw / 2 if anchor == "middle" else tx
        out["labelBoxes"].append({"label": txt, "x": lx, "y": ty - s, "w": tw, "h": s + 4})

    span_len = axis_to - axis_from
    per_day = (plot_r - plot_l) / span_len
    tick_days: list[dict] = []
    if span_len <= SHORT_AXIS:
        widest = text_width(width_of, "12/31", s, 400) + 12
        every = max(1, math.ceil(widest / (7 * per_day)))
        days = _mondays(axis_from, axis_to)
        if not days:
            tick_days.append({"day": axis_from, "label": _fmt_day(axis_from)})
        k = 0
        while k < len(days):
            tick_days.append({"day": days[k], "label": _fmt_day(days[k])})
            k += every
    else:
        tick_days.extend(ticks_of(axis_from, axis_to))
    for t in tick_days:
        tx = px(t["day"])
        out["ticks"].append({"x": tx})
        tw = text_width(width_of, t["label"], s, 400)
        if tx + tw / 2 <= x + w:
            text(t["label"], max(tx, plot_l), y + s + 2, "middle", False, True)

    for i, r in enumerate(rows):
        ry = top + i * ROW_H
        cy = ry + ROW_H / 2
        if _is_section(r):
            out["sections"].append({"x": x, "y": ry, "w": w, "h": ROW_H})
            text(r["section"], x + PAD, cy + s / 2 - 1, "start", True)
            continue
        sp, ep = spans[id(r)]
        text(r["label"], x + PAD, cy + s / 2 - 1, "start")
        if r.get("milestone"):
            mx = px(sp) + per_day / 2
            hh = BAR_H / 2 + 2
            out["bars"].append({"x": mx - hh, "y": cy - hh, "w": 2 * hh, "h": 2 * hh, "tone": r.get("tone", "accent"), "milestone": True, "label": r["label"]})
            if r.get("id"):
                out["anchors"].append({"id": r["id"], "x": mx - hh, "y": cy - hh, "w": 2 * hh, "h": 2 * hh})
            continue
        bx, bw = px(sp), max(4, px(ep) - px(sp))
        rect = {"x": bx, "y": cy - BAR_H / 2, "w": bw, "h": BAR_H}
        bar = {**rect, "tone": r.get("tone", "accent"), "label": r["label"]}
        if r.get("progress") is not None:
            bar["progress"] = r["progress"]
        out["bars"].append(bar)
        if r.get("id"):
            out["anchors"].append({"id": r["id"], **rect})

    def rect_of(t: dict) -> dict:
        return out["bars"][tasks.index(t)]

    for t in tasks:
        for a in afters(t):
            p, q = rect_of(ids[a]), rect_of(t)
            x1, y1 = p["x"] + p["w"], p["y"] + p["h"] / 2
            x2, y2 = q["x"], q["y"] + q["h"] / 2
            between = [b for b in out["bars"] if b is not p and b is not q and b["y"] + b["h"] > min(y1, y2) and b["y"] < max(y1, y2)]

            def free(c: float) -> bool:
                return not any(c >= b["x"] - 4 and c <= b["x"] + b["w"] + 4 for b in between)

            tail_row = rows.index(ids[a])
            head_row = rows.index(t)
            down = head_row > tail_row
            pts = None
            c = x1 + 8
            while c <= x2 - ARROW - 6 and pts is None:
                if free(c):
                    pts = [{"x": x1, "y": y1}, {"x": c, "y": y1}, {"x": c, "y": y2}, {"x": x2, "y": y2}]
                c += 6
            if pts is None:
                b_t = top + (tail_row + 1 if down else tail_row) * ROW_H
                b_h = top + (head_row if down else head_row + 1) * ROW_H
                lo, hi = out["plot"]["x1"] + 4, out["plot"]["x2"] - 4
                if b_t == b_h:
                    cols = [x1 + 8]
                else:
                    candidates = [lo + k * 6 for k in range(math.floor((hi - lo) / 6) + 1)]
                    cols = sorted((c for c in candidates if free(c)), key=lambda c: abs(c - (x1 + x2) / 2))
                if not cols:
                    cols = [x1 + 8]
                pts = [{"x": x1, "y": y1}, {"x": x1 + 8, "y": y1}, {"x": x1 + 8, "y": b_t}, {"x": cols[0], "y": b_t}, {"x": cols[0], "y": b_h}, {"x": x2 - 8, "y": b_h}, {"x": x2 - 8, "y": y2}, {"x": x2, "y": y2}]
            out["deps"].append({"from": tasks.index(ids[a]), "to": tasks.index(t), "points": _simplify_pts(pts)})

    if today_day is not None:
        tx = px(today_day) + per_day / 2
        out["today"] = {"x": tx, "y1": top, "y2": out["plot"]["y2"]}
        tl = today_label or "今日"
        tw = text_width(width_of, tl, s, 700)
        text(tl, min(max(tx, x + tw / 2), x + w - tw / 2), y + HEAD_H - 4, "middle", True, False, "danger")

    return out


def render_gantt(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:381-407 renderGantt()."""
    dim = bool(b.get("dim"))
    ink = PALETTE["muted"] if dim else PALETTE["text"]

    def tone(t: str) -> str:
        if dim:
            return PALETTE["muted"]
        if t == "accent":
            return PALETTE[day]["accent"]
        return PALETTE["danger"] if t == "danger" else PALETTE["muted"]

    def soft(t: str) -> str:
        if dim:
            return PALETTE["bg"]
        return PALETTE[day]["soft"] if t == "accent" else PALETTE["border"]

    out = []
    for sec in b["sections"]:
        out.append(f'<rect x="{snap4(sec["x"])}" y="{snap4(sec["y"])}" width="{snap4(sec["w"])}" height="{sec["h"]}" fill="{PALETTE["code"]}"/>')
    for t in b["ticks"]:
        out.append(f'<path d="M{snap4(t["x"])},{snap4(b["plot"]["y1"])} V{snap4(b["plot"]["y2"])}" fill="none" stroke="{PALETTE["border"]}" stroke-width="1"/>')
    out.append(f'<path d="M{snap4(b["plot"]["x1"])},{snap4(b["plot"]["y1"])} H{snap4(b["plot"]["x2"])}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="2"/>')
    for d in b["deps"]:
        pts = [dict(p) for p in d["points"]]
        n = len(pts)
        tip, prev = pts[n - 1], pts[n - 2]
        length, width = 8, 4
        dx = (tip["x"] > prev["x"]) - (tip["x"] < prev["x"])
        dy = (tip["y"] > prev["y"]) - (tip["y"] < prev["y"])
        pts[n - 1] = {"x": tip["x"] - dx * (length - 1), "y": tip["y"] - dy * (length - 1)}
        line_path = " L".join(f'{snap4(p["x"])},{snap4(p["y"])}' for p in pts)
        head_path = f'M{snap4(tip["x"])},{snap4(tip["y"])} L{snap4(tip["x"] - dx * length - dy * width)},{snap4(tip["y"] - dy * length + dx * width)} L{snap4(tip["x"] - dx * length + dy * width)},{snap4(tip["y"] - dy * length - dx * width)} z'
        out.append(f'<path d="M{line_path}" fill="none" stroke="{ink}" stroke-width="1.5"/>\n  <path d="{head_path}" fill="{ink}"/>')
    for r in b["bars"]:
        if r.get("milestone"):
            cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
            out.append(f'<path d="M{snap4(cx)},{snap4(r["y"])} L{snap4(r["x"] + r["w"])},{snap4(cy)} L{snap4(cx)},{snap4(r["y"] + r["h"])} L{snap4(r["x"])},{snap4(cy)} z" fill="{tone(r["tone"])}" stroke="{PALETTE["bg"]}" stroke-width="2"/>')
            continue
        bx, by, bw = snap4(r["x"]), snap4(r["y"]), snap4(r["w"])
        if r.get("progress") is None:
            out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{r["h"]}" rx="4" fill="{tone(r["tone"])}"/>')
        else:
            out.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{r["h"]}" rx="4" fill="{soft(r["tone"])}" stroke="{tone(r["tone"])}" stroke-width="2"/>')
            if r["progress"] > 0:
                out.append(f'<rect x="{bx}" y="{by}" width="{snap4(r["w"] * r["progress"])}" height="{r["h"]}" rx="4" fill="{tone(r["tone"])}"/>')
    if b.get("today"):
        t = b["today"]
        out.append(f'<path d="M{snap4(t["x"])},{snap4(t["y1"])} V{snap4(t["y2"])}" fill="none" stroke="{PALETTE["muted"] if dim else PALETTE["danger"]}" stroke-width="2"/>')
    for t in b["texts"]:
        anchor_attr = ' text-anchor="middle"' if t["anchor"] == "middle" else (' text-anchor="end"' if t["anchor"] == "end" else "")
        bold_attr = ' font-weight="700"' if t.get("bold") else ""
        fill = PALETTE["muted"] if dim else (PALETTE["danger"] if t.get("tone") == "danger" else (PALETTE["muted"] if t.get("muted") else PALETTE["text"]))
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}"{anchor_attr} font-size="{t["size"]}"{bold_attr} fill="{fill}">{emoji_span(t["text"])}</text>')
    return "\n  ".join(out)
