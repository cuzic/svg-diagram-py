"""1:1 port of lib/people.ts (layoutPeople/layoutDots, both exported — golden-tested live via
the Node CLI, same dummy-width-function technique as atoms.py/wrap.py for the text-dependent
sizing) and the renderPeople/renderDots drawing functions from lib/emit-boxes.ts.

Golden master: lib/people.ts + lib/emit-boxes.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import WidthOf, text_width
from .emit_common import emoji_span, escape_attr, js_round
from .tokens import PALETTE, color_of, text_color_of, tone_style

DOT_GAP, LABEL_GAP, BAR_H, AXIS_GAP = 3, 6, 8, 4
SIDE_GAP = 24

PERSON_BOX = {"from": 4, "size": 16}
PERSON_PATH = "M12 4a4 4 0 1 1 0 8a4 4 0 0 1 0-8M12 14c4.42 0 8 1.79 8 4v2H4v-2c0-2.21 3.58-4 8-4z"


def _snap4(v: float) -> float:
    return js_round(v / 4) * 4


def _ceil4(v: float) -> float:
    return math.ceil(v / 4) * 4


def layout_people(*, cols: int, size: float, gap: float, total: int, count: int, count2: int = 0, x: float, y: float, cw: float, width_of: WidthOf, align: str | None = None, side: dict | None = None, roles: dict) -> dict:
    """lib/people.ts:23-42 layoutPeople()."""
    rows = math.ceil(total / cols)
    gw = cols * size + (cols - 1) * gap
    gh = rows * size + (rows - 1) * gap
    side_size_role = roles.get((side or {}).get("size", "stat"), roles["stat"]) if side else None
    v = side_size_role
    n = roles["note"]
    vw = 0
    if side:
        assert v is not None  # side_size_role is set to a real roles[...] size whenever side is truthy
        vw = text_width(width_of, side["value"], v, 700)
    lw = text_width(width_of, side["label"], n, 400) if side and side.get("label") else 0
    tw = max(vw, lw)
    w = gw + SIDE_GAP + tw if side else gw
    if w > cw:
        extra = " and the number beside them" if side else ""
        raise ValueError(f"people(): {cols} icons of {size}px{extra} are {math.ceil(w)}px wide, the column is {cw}px — use fewer cols, a smaller size or gap")
    left = x if align == "left" else x + (cw - w) / 2
    icons = []
    for i in range(total):
        icon = {"x": left + (i % cols) * (size + gap), "y": y + (i // cols) * (size + gap), "on": i < count + count2}
        if count <= i < count + count2:
            icon["second"] = True
        icons.append(icon)
    texts = []
    h = gh
    if side:
        assert v is not None  # side_size_role is set to a real roles[...] size whenever side is truthy
        th = v * 1.2 + (6 + n * 1.4 if side.get("label") else 0)
        h = max(gh, th)
        top = y + (h - th) / 2
        tx = left + gw + SIDE_GAP
        value_text = {"text": side["value"], "x": tx, "y": top + v, "size": v, "bold": True}
        if side.get("tone") is not None:
            value_text["tone"] = side["tone"]
        texts.append(value_text)
        if side.get("label"):
            texts.append({"text": side["label"], "x": tx, "y": top + v * 1.2 + 6 + n, "size": n, "bold": False, "tone": "muted"})
    return {"x": left, "y": y, "w": w, "h": h, "size": size, "icons": icons, "texts": texts}


def layout_dots(*, r: float, dots: list[dict], zones: list[dict], min_val: float, max_val: float, x: float, y: float, cw: float, width_of: WidthOf, width: float | None = None, low_label: str | None = None, high_label: str | None = None, height: float | None = None, roles: dict) -> dict:
    """lib/people.ts:50-97 layoutDots(). (`min_val`/`max_val` — not `min`/`max` — to avoid
    shadowing the builtins this function needs internally.)"""
    s = roles["note"]
    w = min(width if width is not None else cw, cw)
    left = x + (cw - w) / 2
    plot_l, plot_r = left + r + 2, left + w - r - 2
    if plot_r - plot_l < 80:
        raise ValueError("dots(): the lane is too narrow — raise width")

    def px(v: float) -> float:
        return plot_l + (v - min_val) / (max_val - min_val) * (plot_r - plot_l)

    pitch = _ceil4(2 * r + DOT_GAP)
    last_x: list[float] = []
    sorted_dots = sorted(enumerate(dots), key=lambda iv: (iv[1]["at"], iv[0]))
    placed = []
    for i, d in sorted_dots:
        cx = _snap4(px(d["at"]))
        row = next((k for k, lx in enumerate(last_x) if cx - lx >= pitch), len(last_x))
        if row < len(last_x):
            last_x[row] = cx
        else:
            last_x.append(cx)
        zone = next((z for z in zones if z["from"] <= d["at"] <= z["to"]), None)
        tone = d.get("tone") or (zone["tone"] if zone else None) or "accent"
        placed.append({"x": cx, "row": row, "tone": tone})
    rows = max(1, len(last_x))
    base = _ceil4(BAR_H / 2 + AXIS_GAP + r)
    pile_h = base - r + (rows - 1) * pitch + 2 * r
    labelled = bool(low_label or high_label or zones)
    label_h = (LABEL_GAP + s + 4) if labelled else 0
    need = pile_h + BAR_H / 2 + label_h + 4
    if height is not None and height < need:
        raise ValueError(f"dots(): height {height} is too small for its tallest pile (need at least {math.ceil(need)})")
    h = height if height is not None else need
    axis_y = _ceil4(y + h - BAR_H / 2 - label_h)

    out = {
        "x": left, "y": y, "w": w, "h": h, "r": r,
        "axis": {"x1": _snap4(plot_l), "x2": _snap4(plot_r), "y": axis_y},
        "dots": [{"x": p["x"], "y": axis_y - base - p["row"] * pitch, "tone": p["tone"]} for p in placed],
        "zones": [{"x": _snap4(px(z["from"])), "w": _snap4(px(z["to"])) - _snap4(px(z["from"])), "y": axis_y, "tone": z["tone"], "top": axis_y - _ceil4(base + (rows - 1) * pitch + r)} for z in zones],
        "texts": [],
    }
    boxes: list[dict] = []

    def text(t: str | None, tx: float, anchor: str, clamp: bool = False) -> None:
        if not t:
            return
        tw = text_width(width_of, t, s, 400)
        x1 = tx if anchor == "start" else (tx - tw if anchor == "end" else tx - tw / 2)
        if clamp:
            x1 = max(left, min(left + w - tw, x1))
        if x1 < left - 0.5 or x1 + tw > left + w + 0.5:
            raise ValueError(f'dots(): the label "{t}" leaves the figure — shorten it or raise width')
        for b in boxes:
            if x1 < b["x2"] + 8 and x1 + tw > b["x1"] - 8:
                raise ValueError(f'dots(): the labels "{b["what"]}" and "{t}" overlap — shorten them or raise width')
        boxes.append({"x1": x1, "x2": x1 + tw, "what": t})
        out["texts"].append({"text": t, "x": x1 + tw / 2, "y": y + h - 4, "anchor": "middle", "size": s})

    text(low_label, left, "start")
    text(high_label, left + w, "end")
    for z in zones:
        if z.get("label"):
            text(z["label"], (px(z["from"]) + px(z["to"])) / 2, "middle", True)
    return out


def _n4(v: float) -> str:
    """lib/emit-boxes.ts's `n = (v) => +v.toFixed(4)` for renderPeople: round-to-4-decimals,
    then format the way a JS template literal would (no trailing zeros)."""
    from .emit_common import js_num

    return js_num(round(v, 4))


def _n2(v: float) -> str:
    from .emit_common import js_num

    return js_num(round(v, 2))


def render_people(*, x: float, y: float, size: float, icons: list[dict], texts: list[dict], tone: str | None, tone2: str | None, rest: str | None, alt: str, day: int | str = 1) -> str:
    """lib/emit-boxes.ts:213-219 renderPeople()."""
    s = size / PERSON_BOX["size"]
    color = color_of(tone_style(tone).ink, day)
    color2 = color_of(tone_style(tone2).ink, day)
    rest_color = color_of(tone_style(rest).ink, day)

    def icon(i: dict) -> str:
        tx = _n4(i["x"] - PERSON_BOX["from"] * s)
        ty = _n4(i["y"] - PERSON_BOX["from"] * s)
        if i.get("on"):
            fill = f'fill="{color2 if i.get("second") else color}"'
        else:
            fill = f'fill="none" stroke="{rest_color}" stroke-width="{_n4(1.5 / s)}"'
        return f'<path d="{PERSON_PATH}" transform="translate({tx} {ty}) scale({_n4(s)})" {fill}/>'

    icons_svg = "\n  ".join(icon(i) for i in icons)
    texts_svg = "".join(
        f'\n  <text x="{js_round(t["x"])}" y="{js_round(t["y"])}" font-size="{t["size"]}"{" font-weight=\"700\"" if t.get("bold") else ""} fill="{text_color_of(t.get("tone"), day)}">{emoji_span(t["text"])}</text>'
        for t in texts
    )
    return f'<g role="img" aria-label="{escape_attr(alt)}">\n  {icons_svg}\n  </g>{texts_svg}'


def render_dots(*, axis: dict, zones: list[dict], dots: list[dict], texts: list[dict], r: float, alt: str, day: int | str = 1) -> str:
    """lib/emit-boxes.ts:222-232 renderDots()."""

    def color(tone: str) -> str:
        return color_of(tone_style(tone).ink, day)

    parts = [f'<line x1="{_n2(axis["x1"])}" y1="{_n2(axis["y"])}" x2="{_n2(axis["x2"])}" y2="{_n2(axis["y"])}" stroke="{PALETTE["muted"]}" stroke-width="2"/>']
    for z in zones:
        parts.append(f'<rect x="{_n2(z["x"])}" y="{_n2(z["top"])}" width="{_n2(z["w"])}" height="{_n2(z["y"] - 4 - z["top"])}" fill="{color(z["tone"])}" fill-opacity="0.12"/>')
    for z in zones:
        parts.append(f'<rect x="{_n2(z["x"])}" y="{_n2(z["y"] - 4)}" width="{_n2(z["w"])}" height="8" fill="{color(z["tone"])}"/>')
    dots_svg = "\n    ".join(f'<circle cx="{_n2(p["x"])}" cy="{_n2(p["y"])}" r="{r}" fill="{color(p["tone"])}"/>' for p in dots)
    parts.append(f'<g role="img" aria-label="{escape_attr(alt)}">\n    {dots_svg}\n  </g>')
    for t in texts:
        parts.append(f'<text x="{_n2(t["x"])}" y="{_n2(t["y"])}" text-anchor="{t["anchor"]}" font-size="{t["size"]}" fill="{PALETTE["text"]}">{emoji_span(t["text"])}</text>')
    return "\n  ".join(parts)
