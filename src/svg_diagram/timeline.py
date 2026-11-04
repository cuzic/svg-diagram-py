"""1:1 port of lib/timeline.ts's date-based timeline() — layoutTimeline (exported, golden-
tested live) and renderTimeline (lib/emit-figures.ts, also exported). The numeric-axis
variant (timeline({unit: 'ms', ...}), layoutNumeric) is NOT ported — deferred, see BANDS.md.

Golden master: lib/timeline.ts + lib/emit-figures.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import datetime
import re

from .atoms import WidthOf, text_width
from .emit_common import emoji_span, js_round, snap4
from .tokens import PALETTE, color_of

FLAG_GAP, STEM_MIN, DOT, TICK, MAX_LEVELS = 6, 16, 8, 6, 5
_EPOCH = datetime.date(1970, 1, 1)
_DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
TONE_COLOR = {"accent": "accent", "danger": "danger", "muted": "muted"}


def timeline_day(at: str, what: str) -> int:
    """lib/timeline.ts:10-17 timelineDay()."""
    m = _DATE_RE.match(str(at))
    if not m:
        raise ValueError(f"timeline(): {what} must be 'YYYY', 'YYYY-MM' or 'YYYY-MM-DD' (got {at!r})")
    y, mo, d = int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1)
    try:
        date = datetime.date(y, mo, d)
    except ValueError:
        raise ValueError(f"timeline(): {what} is not a real date ({at})") from None
    return (date - _EPOCH).days


def remaining_text(from_: str, to: str) -> str:
    """lib/timeline.ts:20-29 remainingText()."""
    a, b = timeline_day(from_, "now.at"), timeline_day(to, "deadline.at")
    if a == b:
        return "期限は今日"
    lo, hi = (a, b) if a < b else (b, a)
    low, high = _EPOCH + datetime.timedelta(days=lo), _EPOCH + datetime.timedelta(days=hi)
    months = (high.year - low.year) * 12 + high.month - low.month
    if high.day < low.day:
        months -= 1
    if months < 1:
        span = f"{hi - lo} 日"
    elif months < 12:
        span = f"{months} か月"
    else:
        rem = months % 12
        span = f"{months // 12} 年" + (f" {rem} か月" if rem else "")
    return f"あと {span}" if a < b else f"期限を {span} 過ぎた"


def ticks_of(from_day: float, to_day: float) -> list[dict]:
    """lib/timeline.ts:52-65 ticksOf()."""
    a = _EPOCH + datetime.timedelta(days=from_day)
    months = max(1, (to_day - from_day) / 30.4375)
    step = next((s for s in (1, 3, 6, 12, 24, 60, 120) if months / s <= 8), 120)
    out = []
    y, mth = a.year, a.month - 1
    for _ in range(2000):
        day = (datetime.date(y, mth + 1, 1) - _EPOCH).days
        if day > to_day:
            break
        idx = y if step >= 12 else y * 12 + mth
        if day >= from_day and ((mth == 0 and y % (step // 12) == 0) if step >= 12 else idx % step == 0):
            out.append({"day": day, "label": f"{y}" if mth == 0 else f"{y}/{mth + 1}"})
        mth += 1
        if mth > 11:
            mth = 0
            y += 1
    return out


def _flags_of(now: dict, deadline: dict, marks: list[dict]) -> list[dict]:
    """lib/timeline.ts:34-49 flagsOf()."""
    all_flags = [
        {"label": now.get("label") or "現在", "at": now["at"], "tone": "accent", "bold": True, "big": False},
        {"label": deadline["label"], "at": deadline["at"], "tone": "danger", "bold": True, "big": True},
        *[{"label": m["label"], "at": m["at"], "tone": m.get("tone", "muted"), "bold": False, "big": False} for m in marks],
    ]
    out: list[dict] = []
    for f in all_flags:
        same = next((o for o in out if timeline_day(o["at"], "at") == timeline_day(f["at"], "at")), None)
        if same is None:
            out.append(dict(f))
            continue
        same["label"] += f"・{f['label']}"
        if f["big"]:
            same["big"] = True
            same["tone"] = "danger"
        elif not same["big"] and f["tone"] == "danger":
            same["tone"] = "danger"
        same["bold"] = same["bold"] or f["bold"]
    return out


def _remaining_label(remaining, now_at: str, deadline_at: str) -> str:
    if remaining is False:
        return ""
    return remaining if isinstance(remaining, str) else remaining_text(now_at, deadline_at)


def layout_timeline(*, now: dict, deadline: dict, marks: list[dict] | None, from_: str, to: str, span: str | None, remaining, x: float, y: float, w: float, width_of: WidthOf, roles: dict) -> dict:
    """lib/timeline.ts:80-168 layoutTimeline() (date-based branch only)."""
    marks = marks or []
    s = roles["note"]
    lh = js_round(s * 20 / 14)
    flag_h = 2 * lh
    from_day, to_day = timeline_day(from_, "from"), timeline_day(to, "to")
    plot_l, plot_r = x + 12, x + w - 12
    if plot_r - plot_l < 200:
        raise ValueError("timeline(): the figure is too narrow (200px of axis at least)")

    def px(at: str, what: str) -> float:
        day = timeline_day(at, what)
        if day < from_day or day > to_day:
            raise ValueError(f"timeline(): {what} ({at}) is outside the axis ({from_} - {to})")
        return plot_l + (day - from_day) / (to_day - from_day) * (plot_r - plot_l)

    full = deadline.get("line") == "full"
    dl_at = px(deadline["at"], "deadline.at")
    flags = []
    for f in _flags_of(now, deadline, marks):
        fx = px(f["at"], "at")
        fw = max(text_width(width_of, f["label"], s, 700), text_width(width_of, f["at"], s, 400)) + 8
        flags.append({**f, "x": fx, "w": fw, "left": min(max(fx - fw / 2, x), x + w - fw), "level": -1})

    def hits(a: dict, b: dict) -> bool:
        return not (a["left"] + a["w"] + 6 <= b["left"] or b["left"] + b["w"] + 6 <= a["left"])

    def inside(f: dict, at: float) -> bool:
        return f["left"] - 4 <= at <= f["left"] + f["w"] + 4

    def clamp_left(f: dict, left: float) -> float:
        return min(max(left, x), x + w - f["w"])

    for f in sorted(flags, key=lambda f: -f["x"]):
        is_dl = full and f["big"]
        if is_dl:
            lefts = [clamp_left(f, f["x"] + 6), clamp_left(f, f["x"] - f["w"] - 6)]
        else:
            lefts = [clamp_left(f, f["x"] - 4), f["left"], clamp_left(f, f["x"] - f["w"] + 4)]
        if full:
            if is_dl:
                lefts = [l for l in lefts if l + f["w"] <= f["x"] - 2 or l >= f["x"] + 2]
            else:
                lefts = [l for l in lefts if not (dl_at >= l - 4 and dl_at <= l + f["w"] + 4)]
        for left in lefts:
            k = 0
            while k < MAX_LEVELS and f["level"] < 0:
                f["left"] = left
                if all(o is f or o["level"] < 0 or (not hits(f, o) if o["level"] == k else (not inside(o, f["x"]) if o["level"] < k else not inside(f, o["x"]))) for o in flags):
                    f["level"] = k
                k += 1
        if f["level"] < 0:
            raise ValueError(f'timeline(): the labels near "{f["label"]}" do not fit above the axis; shorten them, drop a mark, or widen the figure')

    levels = max(f["level"] for f in flags) + 1
    fill_span = span == "fill"
    tick_drop = 4 if fill_span else 0
    axis_y = y + levels * (flag_h + FLAG_GAP) + STEM_MIN - FLAG_GAP
    out = {"x": x, "y": y, "w": w, "h": 0, "axis": {"x1": plot_l, "x2": plot_r, "y": axis_y}, "ticks": [], "stems": [], "dots": [], "texts": [], "labelBoxes": []}

    def text(txt: str, tx: float, ty: float, anchor: str, fill: str, bold: bool, w2: float | None = None) -> None:
        out["texts"].append({"text": txt, "x": tx, "y": ty, "anchor": anchor, "fill": fill, "bold": bold, "size": s})
        tw = w2 if w2 is not None else text_width(width_of, txt, s, 700 if bold else 400)
        lx = tx - tw / 2 if anchor == "middle" else (tx - tw if anchor == "end" else tx)
        out["labelBoxes"].append({"label": txt, "x": lx, "y": ty - s, "w": tw, "h": s + 4})

    for f in flags:
        box_bottom = axis_y - STEM_MIN - f["level"] * (flag_h + FLAG_GAP)
        box_top = box_bottom - flag_h
        cx = f["left"] + f["w"] / 2
        out["stems"].append({"x": f["x"], "y1": box_bottom, "y2": axis_y, "tone": TONE_COLOR[f["tone"]]})
        out["dots"].append({"x": f["x"], "y": axis_y, "r": DOT + 4 if f["big"] else DOT, "tone": TONE_COLOR[f["tone"]]})
        text(f["label"], cx, box_top + s + 1, "middle", "text" if f["tone"] == "muted" else f["tone"], True)
        text(f["at"], cx, box_top + lh + s + 1, "middle", "muted", False)

    now_x, dl_x = px(now["at"], "now.at"), px(deadline["at"], "deadline.at")
    out["span"] = {"x1": min(now_x, dl_x), "x2": max(now_x, dl_x), "y": axis_y, "tone": "accent" if now_x <= dl_x else "danger"}
    if fill_span:
        out["span"]["fill"] = True

    ty = axis_y + TICK + s + 2 + tick_drop

    def crosses(left: float, tw: float) -> bool:
        return full and dl_x - 3 <= left + tw and dl_x <= left + tw + 3 and dl_x >= left - 3

    placed = []
    for t in ticks_of(from_day, to_day):
        tx = plot_l + (t["day"] - from_day) / (to_day - from_day) * (plot_r - plot_l)
        out["ticks"].append({"x": tx, "y1": axis_y, "y2": axis_y + TICK})
        tw = text_width(width_of, t["label"], s, 400)
        left = min(max(tx - tw / 2, x), x + w - tw)
        moved = False
        if crosses(left, tw):
            left = dl_x + 6 if tx >= dl_x else dl_x - 6 - tw
            moved = True
        placed.append({"label": t["label"], "left": left, "tw": tw, "moved": moved})

    def clash(a: dict, b: dict) -> bool:
        return a["left"] < b["left"] + b["tw"] + 6 and b["left"] < a["left"] + a["tw"] + 6

    for p in placed:
        if p["moved"] and (p["left"] < x or p["left"] + p["tw"] > x + w or any(o is not p and clash(p, o) for o in placed)):
            continue
        text(p["label"], p["left"], ty, "start", "muted", False, p["tw"])

    bottom = axis_y + TICK + s + 2 + 4 + tick_drop
    rem = _remaining_label(remaining, now["at"], deadline["at"])
    if rem:
        by = bottom + 8
        if out["span"]["x2"] > out["span"]["x1"]:
            out["bracket"] = {"x1": out["span"]["x1"], "x2": out["span"]["x2"], "y": by, "tone": out["span"]["tone"]}
        rw = text_width(width_of, rem, s, 700)
        rl = min(max((out["span"]["x1"] + out["span"]["x2"]) / 2 - rw / 2, x), x + w - rw)
        if crosses(rl, rw):
            rl = dl_x - 6 - rw if out["span"]["x2"] == dl_x else dl_x + 6
        text(rem, rl, by + 6 + s, "start", out["span"]["tone"], True, rw)
        bottom = by + 6 + s + 4

    out["h"] = bottom - y
    if full:
        out["fullLine"] = {"x": dl_x, "y1": y, "y2": y + out["h"]}
    return out


def render_timeline(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:216-234 renderTimeline()."""

    def col(k: str) -> str:
        return PALETTE["muted"] if b.get("dim") else color_of(k, day)

    out = [f'<path d="M{snap4(b["axis"]["x1"])},{snap4(b["axis"]["y"])} H{snap4(b["axis"]["x2"])}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="2"/>']
    span = b.get("span")
    if span and span.get("fill"):
        x1, y1 = snap4(span["x1"]), snap4(span["y"] - 12)
        out.insert(0, f'<rect x="{x1}" y="{y1}" width="{snap4(span["x2"]) - x1}" height="24" fill="{PALETTE[day]["soft"] if span["tone"] == "accent" and not b.get("dim") else PALETTE["border"]}"/>')
    elif span:
        out.append(f'<path d="M{snap4(span["x1"])},{snap4(span["y"])} H{snap4(span["x2"])}" fill="none" stroke="{col(span["tone"])}" stroke-width="8"/>')
    for g in b.get("guides") or []:
        out.append(f'<path d="M{snap4(g["x1"])},{snap4(g["y"])} H{snap4(g["x2"])}" fill="none" stroke="{PALETTE["border"]}" stroke-width="1"/>')
    for r in b.get("bars") or []:
        out.append(f'<rect x="{snap4(r["x"])}" y="{snap4(r["y"])}" width="{snap4(r["x"] + r["w"]) - snap4(r["x"])}" height="{r["h"]}" fill="{col(r["tone"])}" fill-opacity="0.18" stroke="{col(r["tone"])}" stroke-width="2"/>')
    for d in b.get("dims") or []:
        out.append(f'<path d="M{snap4(d["x1"])},{snap4(d["y"])} H{snap4(d["x2"])} M{snap4(d["x1"])},{snap4(d["y"] - 5)} V{snap4(d["y"] + 5)} M{snap4(d["x2"])},{snap4(d["y"] - 5)} V{snap4(d["y"] + 5)}" fill="none" stroke="{col(d["tone"])}" stroke-width="2"/>')
    if b.get("fullLine"):
        fl = b["fullLine"]
        out.append(f'<path d="M{snap4(fl["x"])},{snap4(fl["y1"])} V{snap4(fl["y2"])}" fill="none" stroke="{col("danger")}" stroke-width="2"/>')
    for t in b["ticks"]:
        out.append(f'<path d="M{snap4(t["x"])},{snap4(t["y1"])} V{snap4(t["y2"])}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="2"/>')
    for st in b["stems"]:
        out.append(f'<path d="M{snap4(st["x"])},{snap4(st["y1"])} V{snap4(st["y2"])}" fill="none" stroke="{col(st["tone"])}" stroke-width="2"/>')
    for d in b["dots"]:
        out.append(f'<circle cx="{snap4(d["x"])}" cy="{snap4(d["y"])}" r="{d["r"]}" fill="{col(d["tone"])}" stroke="{PALETTE["bg"]}" stroke-width="4"/>')
    if b.get("bracket"):
        br = b["bracket"]
        out.append(f'<path d="M{snap4(br["x1"])},{snap4(br["y"] - 4)} V{snap4(br["y"])} H{snap4(br["x2"])} V{snap4(br["y"] - 4)}" fill="none" stroke="{col(br["tone"])}" stroke-width="2"/>')
    for t in b["texts"]:
        anchor_attr = "" if t["anchor"] == "start" else f' text-anchor="{t["anchor"]}"'
        bold_attr = ' font-weight="700"' if t.get("bold") else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}"{anchor_attr} font-size="{t["size"]}"{bold_attr} fill="{col(t["fill"])}">{emoji_span(t["text"])}</text>')
    return "\n  ".join(out)
