"""1:1 port of lib/wordart.ts's wordartBand() constructor (defaults + the structural gates
that affect layout — the per-option `check()` type validations are not ported, same scope
decision as flow_shapes.py's band constructors), lib/wordart-layout.ts's layoutWordArt()
(exported, golden-tested live), and lib/emit-wordart.ts's renderWordArt().

Golden master: lib/wordart.ts + lib/wordart-layout.ts + lib/emit-wordart.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
import re

from .atoms import WidthOf, text_width
from .emit_common import emoji_span, js_num, js_round, snap4
from .tokens import MIN_FONT_SIZE, color_of
from .wordart_look import REFLECTION_SHARE, figure_transform, gradient_of, ink_reach, paint_layers, resolve_look, size_of
from .wordart_vertical import BASELINE, COLUMN_PITCH, graphemes, tcy_size, vertical_columns
from .wrap import wrap_text

LINE_H = 1.25  # lib/wordart-layout.ts:32
PLATE_PAD = 0.3
ARC_MIN_KEEP = 0.7
ASCENT = 0.88
DESCENT = 0.2

# ---------------------------------------------------------------------------------------------------------------------------
# constructor
# ---------------------------------------------------------------------------------------------------------------------------


def word_art_band(
    text: str,
    *,
    id: str | None = None,
    reveal: int | None = None,
    until: int | None = None,
    style: str | None = None,
    writing: str | None = None,
    size: float | str | None = None,
    weight: str | None = None,
    font: str | None = None,
    tone: str | None = None,
    gradient: dict | None = None,
    outline=None,
    shadow=None,
    glow=None,
    bevel: bool | None = None,
    extrude=None,
    reflection=None,
    plate: str | None = None,
    spacing: float | None = None,
    arc: float | None = None,
    rotate: float | None = None,
    flip: str | None = None,
    align: str | None = None,
    limit: float | None = None,
) -> dict:
    """lib/wordart.ts:37-72 wordartBand()."""
    if not text or not re.sub(r"[\s​-‍⁠﻿]", "", text):
        raise ValueError("wordart(): needs a non-empty text")
    text = re.sub(r"\r\n?", "\n", text)

    opts: dict = {}
    for k, v in (
        ("style", style), ("writing", writing), ("size", size), ("weight", weight), ("font", font),
        ("tone", tone), ("gradient", gradient), ("outline", outline), ("shadow", shadow), ("glow", glow),
        ("bevel", bevel), ("extrude", extrude), ("reflection", reflection), ("plate", plate),
        ("spacing", spacing), ("arc", arc), ("rotate", rotate), ("flip", flip), ("align", align), ("limit", limit),
    ):
        if v is not None:
            opts[k] = v

    look = resolve_look(opts, MIN_FONT_SIZE)
    if look["fill"] == "none" and not look.get("gradient") and len(look["outlines"]) > 1:
        raise ValueError(
            f"wordart(): hollow letters (tone: none) take one outline, and style '{style or 'bold'}' with this "
            f"outline has {len(look['outlines'])}: the outer ones would fill the letters in (use outline: "
            "{tone, width}, or another style)"
        )
    if arc is not None and writing == "vertical":
        raise ValueError("wordart(): arc bends a horizontal line; it cannot be combined with writing: vertical")
    if arc is not None and len(graphemes(text)) < 2:
        raise ValueError("wordart(): arc bends a line of two letters or more")
    if (reflection or (style == "reflect" and reflection is not False)) and writing == "vertical":
        raise ValueError("wordart(): a reflection is of horizontal text (the columns of vertical text have different lengths)")
    if arc is not None and "\n" in text:
        raise ValueError("wordart(): arc bends one line; the text has a newline")

    band: dict = {"type": "wordart", "text": text, "opts": opts}
    if id is not None:
        band["id"] = id
    if reveal is not None:
        band["reveal"] = reveal
    if until is not None:
        band["until"] = until
    return band


# ---------------------------------------------------------------------------------------------------------------------------
# layout
# ---------------------------------------------------------------------------------------------------------------------------


def _arc_glyphs(text: str, size: float, arc: float, spacing: float, advance) -> dict:
    """lib/wordart-layout.ts:38-58 arcGlyphs()."""
    chars = graphemes(text)
    widths = [advance(c) for c in chars]
    total = sum(widths) + spacing * (len(chars) - 1)
    theta = abs(arc) * math.pi / 180
    r = total / theta
    sign = 1 if arc > 0 else -1
    keep = (r - (DESCENT if sign > 0 else ASCENT) * size) / r
    if keep < ARC_MIN_KEEP:
        raise ValueError(f'wordart(): "{text[:20]}" bent {abs(arc)}° is too tight (the letters would overlap on the inside): use a smaller arc, a longer text or a smaller size')
    raw = []
    corners: list[tuple[float, float]] = []
    at = -total / 2
    for i, ch in enumerate(chars):
        wi = widths[i]
        mid = at + wi / 2
        phi = mid / r
        px, py = r * math.sin(phi), sign * r * (1 - math.cos(phi))
        rot = sign * phi
        c, s = math.cos(rot), math.sin(rot)
        raw.append({"ch": ch, "x": px - wi / 2 * c, "y": py - wi / 2 * s, "rot": rot * 180 / math.pi})
        quad = [(-wi / 2, -ASCENT * size), (wi / 2, -ASCENT * size), (wi / 2, DESCENT * size), (-wi / 2, DESCENT * size)]
        for u, v in quad:
            corners.append((px + u * c - v * s, py + u * s + v * c))
        at += wi + spacing
    min_x, min_y = min(p[0] for p in corners), min(p[1] for p in corners)
    glyphs = [{**g, "x": g["x"] - min_x, "y": g["y"] - min_y} for g in raw]
    w = max(p[0] for p in corners) - min_x
    h = max(p[1] for p in corners) - min_y
    return {"glyphs": glyphs, "w": w, "h": h}


def _set_arc(s: dict, arc: float) -> dict:
    """lib/wordart-layout.ts:66-69 setArc()."""
    a = _arc_glyphs(s["text"], s["size"], arc, s["look"]["spacing"], s["w_of"])
    return {"items": [{"k": "arc", "size": s["size"], "glyphs": a["glyphs"]}], "boxes": [{"x": 0, "y": 0, "w": a["w"], "h": a["h"]}], "w": a["w"], "h": a["h"], "base": a["h"]}


def _set_vertical(s: dict) -> dict:
    """lib/wordart-layout.ts:71-90 setVertical()."""
    size, look = s["size"], s["look"]
    items: list[dict] = []
    boxes: list[dict] = []
    cols = vertical_columns(s["text"], size, look["weight"], s["width_of"], limit=s["opts"].get("limit"), spacing=look["spacing"], font=look["font"])
    pitch = size * COLUMN_PITCH
    w = (len(cols) - 1) * pitch + size
    h = max(c["len"] for c in cols)
    for i, col in enumerate(cols):
        cx = w - size / 2 - i * pitch
        glyphs: list[dict] = []

        def close_run() -> None:
            nonlocal glyphs
            if glyphs:
                items.append({"k": "col", "size": size, "glyphs": glyphs})
            glyphs = []

        for cell in col["cells"]:
            t = cell["token"]
            mid = cell["top"] + cell["len"] / 2
            baseline = cell["top"] + size / 2 + BASELINE * size
            if t["kind"] == "glyph" and not t["turn"]:
                glyphs.append({"ch": t["ch"], "x": cx + t["dx"] * size, "y": baseline + t["dy"] * size, "size": size})
            elif t["kind"] == "tcy":
                glyphs.append({"ch": t["text"], "x": cx, "y": cell["top"] + size / 2 + BASELINE * tcy_size(size), "size": tcy_size(size)})
            elif t["kind"] != "blank":
                close_run()
                items.append({"k": "rot", "text": t["ch"] if t["kind"] == "glyph" else t["text"], "x": cx, "y": mid + BASELINE * size, "cx": cx, "cy": mid, "size": size})
        close_run()
        boxes.append({"x": cx - size / 2, "y": 0, "w": size, "h": col["len"]})
    return {"items": items, "boxes": boxes, "w": w, "h": h, "base": h}


def _set_horizontal(s: dict) -> dict:
    """lib/wordart-layout.ts:92-107 setHorizontal()."""
    size, look = s["size"], s["look"]
    spacing = look["spacing"]
    items: list[dict] = []
    boxes: list[dict] = []
    lines: list[str] = []
    for para in s["text"].split("\n"):
        if para.strip() == "":
            lines.append("")
        else:
            lines.extend(wrap_text(para, max_width=s["room"], atom_width=lambda a: s["w_of"](a) + spacing * len(a), mode=s["mode"]))
    widths = [s["w_of"](l) + spacing * max(0, len(l) - 1) for l in lines]
    w = max(widths)
    h = len(lines) * size * LINE_H
    align = s["opts"].get("align", "center")
    anchor = "start" if align == "start" else ("end" if align == "end" else "middle")
    ax = 0 if align == "start" else (w if align == "end" else w / 2)
    base = h
    for i, line in enumerate(lines):
        if not line:
            continue
        base = i * size * LINE_H + size * ((LINE_H - 1.2) / 2 + 1)
        items.append({"k": "line", "text": line, "x": ax, "y": base, "anchor": anchor, "size": size})
        wl = widths[i]
        box_x = ax - (0 if anchor == "start" else (wl if anchor == "end" else wl / 2))
        boxes.append({"x": box_x, "y": i * size * LINE_H + (size * LINE_H - size * 1.2) / 2, "w": wl, "h": size * 1.2})
    return {"items": items, "boxes": boxes, "w": w, "h": h, "base": base}


def _to_base36(n: int) -> str:
    if n == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(digits[r])
    return "".join(reversed(out))


def _uid_of(text: str, look: dict, at: dict) -> str:
    """lib/wordart-layout.ts:113-117 uidOf() — not byte-matching Node (its hash walks
    JSON.stringify([text, look, ...])); this id only needs to be unique within one rendered
    SVG, and golden tests exclude `uid` from their comparison. See wordart_look._hash36()."""
    h = 5381
    key = repr((text, look, js_round(at["x"]), js_round(at["y"]), js_round(at["w"]), js_round(at["h"])))
    for ch in key:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return f"wa{_to_base36(h)}"


def _turned_box(w: float, h: float, deg: float) -> dict:
    """lib/wordart-layout.ts:120-124 turnedBox()."""
    if deg % 180 == 0:
        return {"w": w, "h": h}
    r = deg * math.pi / 180
    c, n = abs(math.cos(r)), abs(math.sin(r))
    return {"w": w * c + h * n, "h": w * n + h * c}


def translate_item(it: dict, dx: float, dy: float) -> dict:
    """lib/wordart-types.ts:118-124 translateItem()."""
    k = it["k"]
    if k == "line":
        return {**it, "x": it["x"] + dx, "y": it["y"] + dy}
    if k in ("col", "arc"):
        return {**it, "glyphs": [{**g, "x": g["x"] + dx, "y": g["y"] + dy} for g in it["glyphs"]]}
    if k == "rot":
        return {**it, "x": it["x"] + dx, "y": it["y"] + dy, "cx": it["cx"] + dx, "cy": it["cy"] + dy}
    raise ValueError(k)


def layout_word_art(b: dict, x: float, y: float, cw: float, width_of: WidthOf, roles: dict, mode: str) -> dict:
    """lib/wordart-layout.ts:128-151 layoutWordArt()."""
    opts = b["opts"]
    size = size_of(opts.get("size"), roles)
    look = resolve_look(opts, size)
    vertical = opts.get("writing") == "vertical"
    label = re.sub(r"\s+", " ", b["text"]).strip()
    reach = ink_reach(look)
    plate_pad = size * PLATE_PAD if look.get("plate") else 0
    pad_l, pad_r = reach["left"] + plate_pad, reach["right"] + plate_pad
    pad_t, pad_b = reach["top"] + plate_pad, reach["bottom"] + plate_pad

    def w_of(t: str) -> float:
        return text_width(width_of, t, size, look["weight"], look["font"])

    limit = opts.get("limit")
    room = max(size, (limit if limit is not None else cw) - pad_l - pad_r)
    setting = {"text": b["text"], "size": size, "look": look, "opts": opts, "width_of": width_of, "w_of": w_of, "room": room, "mode": mode}

    if opts.get("arc"):
        fig = _set_arc(setting, opts["arc"])
    elif vertical:
        fig = _set_vertical(setting)
    else:
        fig = _set_horizontal(setting)

    ref_h = min(fig["h"], size) * REFLECTION_SHARE if look.get("reflection") else 0
    below = max(0, fig["base"] + look["reflection"]["gap"] + ref_h - fig["h"]) if look.get("reflection") else 0
    w = fig["w"] + pad_l + pad_r
    h = fig["h"] + pad_t + pad_b + below
    turned = _turned_box(w, h, look["rotate"])
    big_w, big_h = turned["w"], turned["h"]
    if big_w > cw + 0.5:
        hint = "lower the size or the spacing, raise limit (taller, fewer columns), or widen the figure" if vertical else "lower the size, shorten it, or widen the figure"
        raise ValueError(f'wordart(): "{label[:20]}" needs {js_round(big_w)}px but the figure is {js_round(cw)}px: {hint}')

    align = opts.get("align", "center")
    ox = x + (0 if align == "start" else (cw - big_w) if align == "end" else (cw - big_w) / 2)
    lx, ly = ox + (big_w - w) / 2, y + (big_h - h) / 2
    off_x, off_y = lx + pad_l, ly + pad_t
    rect = {"x": ox, "y": y, "w": big_w, "h": big_h}
    local = {"x": lx, "y": ly, "w": w, "h": h}
    axis = off_y + fig["base"]
    unmoved = look["rotate"] % 180 == 0 and not look["flipH"] and not look["flipV"]

    result: dict = {"type": "wordart"}
    if b.get("id"):
        result["id"] = b["id"]
    if b.get("reveal") is not None:
        result["reveal"] = b["reveal"]
    if b.get("until") is not None:
        result["until"] = b["until"]
    result["uid"] = _uid_of(label, look, rect)
    result["text"] = label
    result["size"] = size
    result["writing"] = "vertical" if vertical else "horizontal"
    result["look"] = look
    result["items"] = [translate_item(it, off_x, off_y) for it in fig["items"]]
    result.update(rect)
    result["local"] = local
    if look.get("plate"):
        result["plate"] = local
    if look.get("reflection"):
        result["reflection"] = {"axis": axis, "clip": {"x": lx, "y": axis - ref_h, "w": w, "h": ref_h}}
    result["anchors"] = [{"id": b["id"], **rect}] if b.get("id") else []
    result["labelBoxes"] = (
        [{"label": label, "x": off_x + r["x"], "y": off_y + r["y"], "w": r["w"], "h": r["h"]} for r in fig["boxes"]]
        if unmoved
        else [{"label": label, **rect}]
    )
    return result


# ---------------------------------------------------------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------------------------------------------------------


def _snapped(r: dict) -> str:
    x0, y0 = snap4(r["x"]), snap4(r["y"])
    return f'x="{x0}" y="{y0}" width="{snap4(r["x"] + r["w"]) - x0}" height="{snap4(r["y"] + r["h"]) - y0}"'


def _word_art_item(it: dict, band: dict, paint: str, tf: str) -> str:
    """lib/emit-wordart.ts:33-45 wordArtItem()."""
    look = band["look"]
    weight, spacing, font = look["weight"], look["spacing"], look["font"]

    def f1(v: float) -> float:
        return js_round(v * 10) / 10

    def xf(own: str = "") -> str:
        t = " ".join(x for x in (tf, own) if x)
        return f' transform="{t}"' if t else ""

    def head(size: float) -> str:
        cls = ' class="mono"' if font == "mono" else ""
        weight_attr = "" if weight == 400 else f' font-weight="{weight}"'
        return f'{cls} font-size="{js_num(size)}"{weight_attr} {paint}'

    def at(x: float, y: float) -> str:
        return f'x="{js_num(f1(x))}" y="{js_num(f1(y))}"'

    k = it["k"]
    if k == "line":
        anchor_attr = "" if it["anchor"] == "start" else f' text-anchor="{it["anchor"]}"'
        spacing_attr = f' letter-spacing="{js_num(spacing)}"' if spacing else ""
        return f'<text {at(it["x"], it["y"])}{anchor_attr}{spacing_attr}{xf()}{head(it["size"])}>{emoji_span(it["text"])}</text>'

    if k == "rot":
        own = f'rotate(90 {js_num(f1(it["cx"]))} {js_num(f1(it["cy"]))})'
        return f'<text {at(it["x"], it["y"])} text-anchor="middle"{xf(own)}{head(it["size"])}>{emoji_span(it["text"])}</text>'

    if k == "arc":
        first = it["glyphs"][0]
        tspans = "".join(f'<tspan {at(g["x"], g["y"])} rotate="{js_num(f1(g["rot"]))}">{emoji_span(g["ch"])}</tspan>' for g in it["glyphs"])
        return f'<text {at(first["x"], first["y"])}{xf()}{head(it["size"])}>{tspans}</text>'

    if k == "col":
        first = it["glyphs"][0]
        parts = []
        for g in it["glyphs"]:
            size_attr = "" if g["size"] == it["size"] else f' font-size="{js_num(g["size"])}"'
            parts.append(f'<tspan {at(g["x"], g["y"])}{size_attr}>{emoji_span(g["ch"])}</tspan>')
        return f'<text {at(first["x"], first["y"])} text-anchor="middle"{xf()}{head(it["size"])}>{"".join(parts)}</text>'

    raise ValueError(k)


def render_word_art(band: dict, day: int | str = 1, dim: bool = False) -> str:
    """lib/emit-wordart.ts:10-30 renderWordArt()."""
    parts: list[str] = []
    look = band["look"]

    def f1(v: float) -> float:
        return js_round(v * 10) / 10

    g = None if dim else gradient_of(band, day)
    defs = []
    if g:
        defs.append(
            f'<linearGradient id="{g["id"]}" gradientUnits="userSpaceOnUse" '
            f'x1="{js_num(f1(g["x1"]))}" y1="{js_num(f1(g["y1"]))}" x2="{js_num(f1(g["x2"]))}" y2="{js_num(f1(g["y2"]))}">'
            f'<stop offset="0" stop-color="{g["from"]}"/><stop offset="1" stop-color="{g["to"]}"/></linearGradient>'
        )
    if band.get("reflection") and not dim:
        defs.append(f'<clipPath id="{band["uid"]}-c"><rect {_snapped(band["reflection"]["clip"])}/></clipPath>')
    if defs:
        parts.append(f'<defs>{"".join(defs)}</defs>')

    figure = figure_transform(band)
    if band.get("plate") and not dim:
        tf_attr = f' transform="{figure}"' if figure else ""
        parts.append(f'<rect {_snapped(band["plate"])} rx="{js_num(js_round(band["size"] * 0.15))}" fill="{color_of(look["plate"], day)}"{tf_attr}/>')

    for p in paint_layers(band, day, dim):
        if p.get("stroke"):
            paint_order = ' paint-order="stroke"' if p.get("text") and p["fill"] != "none" else ""
            stroke = f' stroke="{p["stroke"]}" stroke-width="{js_num(p["sw"])}" stroke-linejoin="round"{paint_order}'
        else:
            stroke = ""
        opacity = f' opacity="{js_num(p["opacity"])}"' if p.get("opacity") is not None else ""
        decor = ' aria-hidden="true" data-decor=""' if p.get("hidden") else ""
        clip = f' clip-path="url(#{band["uid"]}-c)"' if p.get("mirror") else ""
        paint = f'fill="{p["fill"]}"{stroke}{opacity}{decor}{clip}'
        if p.get("mirror") and band.get("reflection"):
            mirror = f'matrix(1 0 0 -1 0 {js_num(f1(2 * band["reflection"]["axis"] + look["reflection"]["gap"]))})'
        else:
            mirror = ""
        tf = " ".join(x for x in (figure, mirror) if x)
        parts.append("\n  ".join(_word_art_item(translate_item(it, p["dx"], p["dy"]), band, paint, tf) for it in band["items"]))

    return "\n  ".join(parts)
