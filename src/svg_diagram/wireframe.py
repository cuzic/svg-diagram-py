"""1:1 port of lib/wireframe.ts's layoutWireframe()/layoutScreens() (both exported,
golden-tested live) and lib/emit-tables.ts's renderPrims().

A screen is a tree of nodes, each a plain dict with a "t" key (e.g. {"t": "col",
"children": [...]}) — same shape as Node's WfNode, so a node tree can be sent to both
sides unchanged in a golden test. Layout is a small flex engine (col/row/card + leaf
widgets); the result is a flat list of drawing primitives (rect/text/path/circle/badge/
pill) in absolute coordinates, with colours as TOKEN KEYS resolved against the day
theme by render_prims(), same as the rest of this port.

Scope: lib/wireframe-parts.ts ("installParts" — states: missing/disconnected/loading/
empty/stale on any node, and the fusion/compare/region/robot/battery/signal/insight/
breadcrumb/toggle/checkbox/radio/slider node kinds, all for monitoring-style screens)
is NOT ported — a large, specialized extension on top of the already-large core engine
below. A node's `state`/`stateTitle`/`stateNote`/`parts` fields are therefore ignored.
A map marker's `id`/`shape`/`fov`/`heading` (the "robot glyph" decorations, also from
wireframe-parts.ts) raise NotImplementedError — same pattern as render_connect()'s
weight:'strong'/line:'double'. The `wf.*` node-constructor sugar, diagram-level
wireframeDefaults/shell, and stateRow()/matrix part-rows (DSL-level conveniences) are
not ported either: callers build the node tree as plain dicts directly.

Golden master: lib/wireframe.ts + lib/emit-tables.ts's renderPrims() (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
import re
from typing import Callable

from .atoms import WidthOf, split_atoms, text_width
from .badge import BadgeShape, badge_box, badge_svg, pill_svg
from .emit_common import emoji_span, escape_xml, js_num, js_round, snap4
from .tokens import PALETTE, TONE_ALIAS, color_of, text_key_of, tone_style
from .wrap import WrapMode, wrap_atoms

S, T, LHF, GAP = 14, 15, 1.4, 12
VISUAL = {"map", "video", "heat", "pointcloud", "chart", "image"}
CONTAINER = {"col", "row", "card"}


def _lh(size: float) -> float:
    return size * LHF


# ---- drawing context -----------------------------------------------------------------------
def _mk_ctx(width_of: WidthOf, wrap_mode: WrapMode, skeleton: bool | None = False) -> dict:
    return {"widthOf": width_of, "wrap": wrap_mode, "skeleton": bool(skeleton), "prims": [], "callouts": [], "all": [], "used": set()}


_KATA_RE = re.compile(r"^[゠-ヿ]+$")


def _tw(ctx: dict, s, size: float, weight: int) -> float:
    return text_width(ctx["widthOf"], str(s), size, weight)


def _atoms_of(s) -> list[str]:
    """lib/wireframe.ts:96-103 atomsOf(): katakana runs stay in one piece (ドラッグ must
    not break as ドラッ/グ); widths are summed per character."""
    out: list[str] = []
    for a in split_atoms(str(s)):
        if out and _KATA_RE.match(a) and _KATA_RE.match(out[-1]):
            out[-1] += a
        else:
            out.append(a)
    return out


def _wrap_t(ctx: dict, s, size: float, weight: int, max_w: float) -> list[str]:
    return wrap_atoms(_atoms_of(s), max_width=max(24, max_w), atom_width=lambda a: _tw(ctx, a, size, weight), mode=ctx["wrap"])


def _opt(**kv) -> dict:
    """Node's object literals drop a key whose value is `undefined` when serialized to
    JSON; a Python dict with that key set to None does not, so prims that would carry an
    unset optional field (dash/op/cap/anchor) omit the key entirely instead."""
    return {k: v for k, v in kv.items() if v is not None}


def _rect(ctx: dict, x: float, y: float, w: float, h: float, *, r: float = 0, fill: str | None = None, stroke: str | None = None, sw: float = 2, dash: str | None = None, op: float | None = None) -> None:
    ctx["prims"].append({"k": "rect", "x": x, "y": y, "w": w, "h": h, "r": r, "fill": fill, "stroke": stroke, "sw": sw, **_opt(dash=dash, op=op)})


def _circle(ctx: dict, cx: float, cy: float, r: float, *, fill: str | None = None, stroke: str | None = None, sw: float = 2, op: float | None = None) -> None:
    ctx["prims"].append({"k": "circle", "cx": cx, "cy": cy, "r": r, "fill": fill, "stroke": stroke, "sw": sw, **_opt(op=op)})


def _text(ctx: dict, s, x: float, base: float, *, size: float = S, weight: int = 400, fill: str = "text", anchor: str | None = None) -> None:
    ctx["prims"].append({"k": "text", "s": str(s), "x": x, "y": base, "size": size, "weight": weight, "fill": fill, **_opt(anchor=anchor)})


def _badge(ctx: dict, cx: float, cy: float, label, *, r: float | None = None, shape: BadgeShape = "circle", fill: str = "accent", aria: str | None = None) -> dict:
    rr = r if r is not None else 11
    s = str(label)
    box = badge_box(cx, cy, _tw(ctx, s, S, 700), rr, shape)
    ctx["prims"].append({"k": "badge", "cx": cx, "cy": cy, "r": rr, "w": box["w"], "shape": shape, "label": s, "aria": aria if aria is not None else s, "size": S, "fill": fill})
    return box


def _pts(ps: list[tuple[float, float]]) -> str:
    return " ".join(f"{'L' if i else 'M'}{js_round(x)},{js_round(y)}" for i, (x, y) in enumerate(ps))


def _path(ctx: dict, d: str, *, fill: str | None = None, stroke: str | None = None, sw: float = 2, dash: str | None = None, op: float | None = None, cap: str | None = None) -> None:
    ctx["prims"].append({"k": "path", "d": d, "fill": fill, "stroke": stroke, "sw": sw, **_opt(dash=dash, op=op, cap=cap)})


def _line(ctx: dict, x1: float, y1: float, x2: float, y2: float, *, stroke: str = "border", sw: float = 2, dash: str | None = None, op: float | None = None) -> None:
    _path(ctx, _pts([(x1, y1), (x2, y2)]), fill=None, stroke=stroke, sw=sw, dash=dash, op=op)


def _mid(cy: float, size: float = S) -> float:
    return cy + size * 0.36


def _grid(v: float) -> float:
    return js_round(v / 4) * 4


def _tone_of(t: str | None) -> str:
    if t is not None:
        return TONE_ALIAS.get(t, t)
    return "plain"


def _tone_fill(t: str | None) -> str:
    return text_key_of(t)


def _chip_w(ctx: dict, label: str) -> float:
    return _tw(ctx, label, S, 700) + 20


def _draw_chip(ctx: dict, label: str, x: float, y: float, tone: str | None = None) -> float:
    st = tone_style(tone)
    w = _chip_w(ctx, label)
    ctx["prims"].append({"k": "pill", "x": x, "y": y, "w": w, "h": 24, "label": label, "size": S, "base": _mid(y + 12), "fill": st.fill, "stroke": st.chip_stroke or st.stroke, "text": st.text})
    return w


def _chip_spec(c) -> dict:
    return {"text": c} if isinstance(c, str) else c


def _bars(ctx: dict, widths: list[float], x: float, y: float, size: float = S) -> None:
    for k, bw in enumerate(widths):
        _rect(ctx, x, y + k * _lh(size) + 6, max(12, bw), 8, r=4, fill="border")


# ---- layout helpers -------------------------------------------------------------------------
def _auto_w(n: dict, ctx: dict) -> float | None:
    if n["t"] == "btn":
        return _tw(ctx, n["label"], S, 700) + 28
    if n["t"] == "chip":
        return _chip_w(ctx, n["label"])
    return None


def _flex_of(n: dict) -> float:
    flex = n.get("flex")
    if flex is not None:
        return flex
    return 1 if n["t"] in VISUAL and n.get("h") is None else 0


def _label(n: dict) -> str:
    title, label, text, children = n.get("title"), n.get("label"), n.get("text"), n.get("children")
    if title is not None:
        return title
    if label is not None:
        return label
    if text is not None:
        return text
    if children is not None:
        return f"{n['t']} of {' / '.join(c['t'] for c in children)}"
    return n["t"]


def _row_widths(n: dict, w: float, ctx: dict) -> list[float]:
    gap = n.get("gap", GAP)
    kids = n["children"]
    avail = w - gap * max(0, len(kids) - 1)
    fixed: list[float | None] = [c["w"] if c.get("w") is not None else (_auto_w(c, ctx) if c.get("flex") is None else None) for c in kids]
    used = sum(v or 0 for v in fixed)
    flex_sum = sum((kids[i].get("flex", 1) if fixed[i] is None else 0) for i in range(len(kids)))
    out: list[float] = []
    for i, c in enumerate(kids):
        v = fixed[i]
        out.append(v if v is not None else (max(40.0, (avail - used) * c.get("flex", 1) / flex_sum) if flex_sum else 0.0))
    return out


def _col_nat(children: list[dict], w: float, gap: float, ctx: dict) -> float:
    return sum(_nat(c, w, ctx) for c in children) + gap * max(0, len(children) - 1)


# ---- natural heights -------------------------------------------------------------------------
def _wf_text_lines(n: dict, w: float, ctx: dict) -> list[str]:
    size = T if n.get("size") == "title" else S
    weight = 700 if (n.get("bold") or n.get("size") == "title") else 400
    return _wrap_t(ctx, n["text"], size, weight, w)


def _list_rows(n: dict, w: float, ctx: dict) -> list[dict]:
    out = []
    for it in n["items"]:
        o = {"text": it} if isinstance(it, str) else it
        bw = _chip_w(ctx, o["badge"]) + 8 if o.get("badge") else 0
        lines = _wrap_t(ctx, o["text"], S, 700 if o.get("active") else 400, w - 20 - bw)
        out.append({"o": o, "lines": lines, "bw": bw, "h": max(32.0, len(lines) * _lh(S) + 12)})
    return out


def _kv_rows(n: dict, w: float, ctx: dict) -> dict:
    pairs = [{"k": p[0], "v": p[1]} if isinstance(p, (list, tuple)) else p for p in n["pairs"]]
    key_w = n.get("keyW")
    if key_w is None:
        key_w = min(w * 0.5, max(_tw(ctx, p["k"], S, 400) for p in pairs) + 12)
    rows = []
    for p in pairs:
        lines = _wrap_t(ctx, p["v"], S, 400, w - key_w)
        rows.append({**p, "lines": lines, "h": max(24.0, len(lines) * _lh(S) + 4)})
    return {"keyW": key_w, "rows": rows}


def _table_data(n: dict, w: float, ctx: dict) -> dict:
    cols: list[dict] = [{"label": c} if isinstance(c, str) else c for c in n["columns"]]
    total_flex = sum(c.get("flex", 1) for c in cols)
    cw = [w * c.get("flex", 1) / total_flex for c in cols]
    rows = []
    for r in n["rows"]:
        cells: list[dict] = []
        for i, cell in enumerate(r):
            c: dict = {"text": str(cell)} if isinstance(cell, (str, int, float)) else dict(cell)
            lines = [] if c.get("badge") else _wrap_t(ctx, c.get("text", ""), S, 700 if c.get("bold") else 400, cw[i] - 16)
            c["lines"] = lines
            cells.append(c)
        h = max(32.0 if any(c.get("badge") for c in cells) else 28.0, max((len(c["lines"]) for c in cells), default=0) * _lh(S) + 8)
        rows.append({"cells": cells, "h": h})
    return {"cols": cols, "cw": cw, "rows": rows}


def _nat(n: dict, w: float, ctx: dict) -> float:
    """lib/wireframe.ts:198-224 nat()/natBase(), without the `state` branch (see module
    docstring — wireframe-parts.ts's stateMinH() is not ported)."""
    if n.get("h") is not None:
        return n["h"]
    t = n["t"]
    if t == "spacer":
        return 8.0
    if t == "text":
        return max(1, len(_wf_text_lines(n, w, ctx))) * _lh(T if n.get("size") == "title" else S)
    if t in ("btn", "input", "select"):
        return 32.0
    if t == "chip":
        return 24.0
    if t == "tabs":
        return 36.0
    if t == "appbar":
        return 44.0
    if t == "seek":
        return 28.0
    if t == "stat":
        return 88.0
    if t == "kv":
        return sum(r["h"] for r in _kv_rows(n, w, ctx)["rows"])
    if t == "list":
        return (32 if n.get("title") else 0) + sum(r["h"] for r in _list_rows(n, w, ctx))
    if t == "table":
        d = _table_data(n, w, ctx)
        return 28 + sum(r["h"] for r in d["rows"])
    if t == "alert":
        return max(36.0, len(_wrap_t(ctx, n["text"], S, 700, w - 44)) * _lh(S) + 16)
    if t == "col":
        p = n.get("pad", 0)
        return _col_nat(n["children"], w - 2 * p, n.get("gap", GAP), ctx) + 2 * p
    if t == "row":
        p = n.get("pad", 0)
        ws = _row_widths(n, w - 2 * p, ctx)
        return max([_nat(c, ws[i], ctx) for i, c in enumerate(n["children"])], default=0.0) + 2 * p
    if t == "card":
        p = n.get("pad", 10)
        return (28 if n.get("title") else 0) + _col_nat(n["children"], w - 2 * p, n.get("gap", GAP), ctx) + 2 * p
    return n.get("min", 100 if t == "chart" else 80)


# ---- placement -------------------------------------------------------------------------------
def _place(n: dict, x: float, y: float, w: float, h: float | None, ctx: dict) -> dict:
    """lib/wireframe.ts:227-242 place(), without the `state` branch."""
    natural = _nat(n, w, ctx)
    hh = h if h is not None else natural
    if n["t"] in CONTAINER and natural > hh + 1:
        raise ValueError(f'wireframe(): "{_label(n)}" ({n["t"]}) needs {math.ceil(natural)}px of height but only {math.floor(hh)}px is available — raise h or remove content')
    r = _DRAW[n["t"]](n, x, y, w, hh, ctx) if n["t"] in _DRAW else None
    if r is None:
        raise ValueError(f'wireframe(): unknown node type "{n["t"]}"')
    if n.get("mark"):
        ctx["used"].add(n["mark"])
        _rect(ctx, x - 3, y - 3, r["w"] + 6, r["h"] + 6, r=8, stroke="accent", sw=2.5, dash="6,4" if n["mark"] == "new" else None)
    if n.get("n") is not None:
        ctx["callouts"].append({"n": n["n"], "x": x + 12, "y": y - (9 if n.get("mark") else 6)})
    return r


def _place_col(children: list[dict], x: float, y: float, w: float, h: float, gap: float, ctx: dict) -> None:
    nat_h = [_nat(c, w, ctx) for c in children]
    total = sum(nat_h) + gap * max(0, len(children) - 1)
    flex_sum = sum(_flex_of(c) for c in children)
    extra = max(0.0, h - total) if flex_sum else 0.0
    cy = y
    for i, c in enumerate(children):
        ch = nat_h[i] + (extra * _flex_of(c) / flex_sum if flex_sum else 0)
        _place(c, x, cy, w, ch, ctx)
        cy += ch + gap


# ---- draw table ------------------------------------------------------------------------------
def _draw_col(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    p = n.get("pad", 0)
    _place_col(n["children"], x + p, y + p, w - 2 * p, h - 2 * p, n.get("gap", GAP), ctx)
    return {"w": w, "h": h}


def _draw_row(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    p = n.get("pad", 0)
    gap = n.get("gap", GAP)
    ws = _row_widths(n, w - 2 * p, ctx)
    cx = x + p
    for i, c in enumerate(n["children"]):
        ch = h - 2 * p
        wi = ws[i]
        own = _nat(c, wi, ctx)
        dy = (ch - own) / 2 if n.get("align") == "center" and _flex_of(c) == 0 else 0
        _place(c, cx, y + p + dy, wi, ch if (_flex_of(c) or c["t"] in VISUAL or c["t"] in CONTAINER) else own, ctx)
        cx += wi + gap
    return {"w": w, "h": h}


def _draw_card(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    p = n.get("pad", 10)
    _rect(ctx, x, y, w, h, r=8, fill="code" if n.get("tone") == "muted" else "bg", stroke="border")
    if n.get("title"):
        _text(ctx, n["title"], x + p, y + p + T, size=T, weight=700)
    top = 28 if n.get("title") else 0
    _place_col(n["children"], x + p, y + p + top, w - 2 * p, h - 2 * p - top, n.get("gap", GAP), ctx)
    return {"w": w, "h": h}


def _draw_text(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    size = T if n.get("size") == "title" else S
    weight = 700 if (n.get("bold") or n.get("size") == "title") else 400
    lines = _wf_text_lines(n, w, ctx)
    fill = _tone_fill(n.get("tone"))
    ax = x + w / 2 if n.get("align") == "center" else (x + w if n.get("align") == "right" else x)
    anchor = "middle" if n.get("align") == "center" else ("end" if n.get("align") == "right" else None)
    if ctx["skeleton"] and not n.get("keep"):
        _bars(ctx, [_tw(ctx, l, size, weight) for l in lines], x, y, size)
    else:
        for k, l in enumerate(lines):
            _text(ctx, l, ax, y + size + k * _lh(size), size=size, weight=weight, fill=fill, anchor=anchor)
    return {"w": w, "h": max(1, len(lines)) * _lh(size)}


def _draw_btn(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    bw = w if n.get("full") else min(w, _auto_w(n, ctx) or 0)
    primary = bool(n.get("primary"))
    _rect(ctx, x, y, bw, 32, r=6, fill=("danger" if n.get("danger") else "accent") if primary else "bg", stroke=None if primary else ("danger" if n.get("danger") else "text"))
    _text(ctx, n["label"], x + bw / 2, _mid(y + 16), weight=700, fill="bg" if primary else ("danger" if n.get("danger") else "text"), anchor="middle")
    return {"w": bw, "h": 32}


def _draw_chip_node(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    return {"w": _draw_chip(ctx, n["label"], x, y, n.get("tone")), "h": 24}


def _draw_input(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    _rect(ctx, x, y, w, 32, r=6, fill="bg", stroke="muted")
    _text(ctx, n["label"], x + 10, _mid(y + 16), fill="text" if n.get("value") else "muted")
    return {"w": w, "h": 32}


def _draw_select(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    _rect(ctx, x, y, w, 32, r=6, fill="bg", stroke="muted")
    _text(ctx, n["label"], x + 10, _mid(y + 16), fill="text" if n.get("value") else "muted")
    _path(ctx, f"M{js_round(x + w - 24)},{js_round(y + 13)} L{js_round(x + w - 12)},{js_round(y + 13)} L{js_round(x + w - 18)},{js_round(y + 20)} Z", fill="muted")
    return {"w": w, "h": 32}


def _draw_tabs(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    active = n.get("active", 0)
    _line(ctx, x, y + 34, x + w, y + 34, stroke="border")
    cx = x
    for i, l in enumerate(n["labels"]):
        tab = _tw(ctx, l, S, 700) + 28
        _text(ctx, l, cx + tab / 2, _mid(y + 17), weight=700 if i == active else 400, fill="accent" if i == active else "muted", anchor="middle")
        if i == active:
            _line(ctx, cx, y + 34, cx + tab, y + 34, stroke="accent", sw=4)
        cx += tab
    return {"w": w, "h": 36}


def _draw_appbar(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    _rect(ctx, x, y, w, 44, fill="accent")
    _text(ctx, n["title"], x + 14, _mid(y + 22), weight=700, fill="bg")
    cx = x + 14 + _tw(ctx, n["title"], S, 700) + 28
    if ctx["skeleton"]:
        for l in n.get("nav") or []:
            lw = min(40.0, _tw(ctx, l, S, 400) / 2)
            if cx + lw < x + w - 12:
                _rect(ctx, cx, y + 18, lw, 8, r=4, fill="bg", op=0.7)
            cx += lw + 12
        return {"w": w, "h": 44}
    for i, l in enumerate(n.get("nav") or []):
        active = i == n.get("active", -1)
        _text(ctx, l, cx, _mid(y + 22), weight=700 if active else 400, fill="bg")
        lw = _tw(ctx, l, S, 700 if active else 400)
        if active:
            _line(ctx, cx, y + 34, cx + lw, y + 34, stroke="bg", sw=3)
        cx += lw + 24
    rx = x + w - 14
    for l in reversed(n.get("right") or []):
        _text(ctx, l, rx, _mid(y + 22), fill="bg", anchor="end")
        rx -= _tw(ctx, l, S, 400) + 20
    return {"w": w, "h": 44}


def _draw_seek(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    lw = _tw(ctx, n["from"], S, 400) + 8 if n.get("from") else 0
    rw = _tw(ctx, n["to"], S, 400) + 8 if n.get("to") else 0
    x0, x1, cy = x + 28 + lw, x + w - rw - 8, y + 14
    _path(ctx, _pts([(x + 6, cy - 8), (x + 6, cy + 8), (x + 20, cy)]) + " Z", fill="accent")
    if n.get("from"):
        _text(ctx, n["from"], x + 28, _mid(cy), fill="muted")
    if n.get("to"):
        _text(ctx, n["to"], x + w - 4, _mid(cy), fill="muted", anchor="end")
    _line(ctx, x0, cy, x1, cy, stroke="border", sw=4)
    at = x0 + (x1 - x0) * n.get("at", 0.4)
    _line(ctx, x0, cy, at, cy, stroke="accent", sw=4)
    for m in n.get("marks") or []:
        _line(ctx, x0 + (x1 - x0) * m, cy - 8, x0 + (x1 - x0) * m, cy + 8, stroke="danger", sw=3)
    _circle(ctx, at, cy, 7, fill="accent", stroke="bg")
    return {"w": w, "h": 28}


def _draw_kv(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    data = _kv_rows(n, w, ctx)
    key_w, rows = data["keyW"], data["rows"]
    cy = y
    for r in rows:
        _text(ctx, r["k"], x, cy + 2 + S, fill="muted")
        for k, l in enumerate(r["lines"]):
            _text(ctx, l, x + key_w, cy + 2 + S + k * _lh(S), fill=_tone_fill(_tone_of(r.get("tone"))), weight=700 if r.get("bold") else 400)
        cy += r["h"]
    return {"w": w, "h": cy - y}


def _draw_stat(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    tone = _tone_of(n.get("tone"))
    _rect(ctx, x, y, w, 88, r=8, fill="bg" if tone == "danger" else "code", stroke="danger" if tone == "danger" else "border")
    _text(ctx, n["value"], x + w / 2, y + 52, size=34, weight=700, fill=_tone_fill(tone), anchor="middle")
    _text(ctx, n["label"], x + w / 2, y + 76, fill="muted", anchor="middle")
    return {"w": w, "h": 88}


def _draw_list(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    cy = y
    if n.get("title"):
        _text(ctx, n["title"], x, cy + 20, size=T, weight=700)
        _line(ctx, x, cy + 31, x + w, cy + 31, stroke="border")
        cy += 32
    for r in _list_rows(n, w, ctx):
        o, lines, bw, rh = r["o"], r["lines"], r["bw"], r["h"]
        if o.get("active"):
            _rect(ctx, x, cy, w, rh, r=4, fill="soft")
        if ctx["skeleton"] and not o.get("keep"):
            _bars(ctx, [_tw(ctx, l, S, 400) for l in lines], x + 10, cy + (rh - _lh(S) * len(lines)) / 2 - 6)
        else:
            for k, l in enumerate(lines):
                _text(ctx, l, x + 10, cy + (rh - _lh(S) * len(lines)) / 2 + S + k * _lh(S), weight=700 if o.get("active") else 400)
        if o.get("badge"):
            _draw_chip(ctx, o["badge"], x + w - bw + 8 - 6, cy + (rh - 24) / 2, o.get("tone"))
        _line(ctx, x, cy + rh, x + w, cy + rh, stroke="border", sw=1.5)
        cy += rh
    return {"w": w, "h": cy - y}


def _draw_table(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    d = _table_data(n, w, ctx)
    total = _nat(n, w, ctx)
    _rect(ctx, x, y, w, 28, fill="soft")
    cx = x
    for i, c in enumerate(d["cols"]):
        _text(ctx, c["label"], cx + 8, _mid(y + 14), weight=700)
        cx += d["cw"][i]
    cy = y + 28
    for r in d["rows"]:
        _line(ctx, x, cy, x + w, cy, stroke="border", sw=1.5)
        cx = x
        for i, c in enumerate(r["cells"]):
            if c.get("badge"):
                _draw_chip(ctx, c["badge"], cx + 8, cy + (r["h"] - 24) / 2, c.get("tone"))
            elif ctx["skeleton"] and not c.get("keep"):
                _bars(ctx, [_tw(ctx, l, S, 400) for l in c["lines"]], cx + 8, cy + (r["h"] - _lh(S) * len(c["lines"])) / 2 - 6)
            else:
                for k, l in enumerate(c["lines"]):
                    _text(ctx, l, cx + 8, cy + (r["h"] - _lh(S) * len(c["lines"])) / 2 + S + k * _lh(S), weight=700 if c.get("bold") else 400, fill=_tone_fill(_tone_of(c.get("tone"))))
            cx += d["cw"][i]
        cy += r["h"]
    _rect(ctx, x, y, w, total, r=6, stroke="border")
    return {"w": w, "h": total}


def _draw_alert(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    tone = _tone_of(n.get("tone"))
    t = tone_style(tone if tone in ("danger", "accent") else None)
    if tone in ("danger", "accent"):
        st = {"fill": t.fill, "stroke": t.stroke or t.fill, "text": t.text if tone == "danger" else "text"}
    else:
        st = {"fill": "code", "stroke": "border", "text": "text"}
    lines = _wrap_t(ctx, n["text"], S, 700, w - 44)
    hh = max(36.0, len(lines) * _lh(S) + 16)
    _rect(ctx, x, y, w, hh, r=6, fill=st["fill"], stroke=st["stroke"])
    _badge(ctx, x + 18, y + hh / 2, "!", r=9, fill="danger" if tone == "danger" else "accent", aria="警告" if tone == "danger" else "注意")
    for k, l in enumerate(lines):
        _text(ctx, l, x + 36, y + (hh - _lh(S) * len(lines)) / 2 + S + k * _lh(S), weight=700, fill=st["text"])
    return {"w": w, "h": hh}


def _draw_image(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    _rect(ctx, x, y, w, h, r=6, fill="code", stroke="border")
    _line(ctx, x + 1, y + 1, x + w - 1, y + h - 1, stroke="border", sw=1.5)
    _line(ctx, x + w - 1, y + 1, x + 1, y + h - 1, stroke="border", sw=1.5)
    lw = _tw(ctx, n["label"], S, 400) + 16
    _rect(ctx, x + w / 2 - lw / 2, y + h / 2 - 12, lw, 24, r=4, fill="code")
    _text(ctx, n["label"], x + w / 2, _mid(y + h / 2), fill="muted", anchor="middle")
    return {"w": w, "h": h}


def _draw_video(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    _rect(ctx, x, y, w, h, r=6, fill="code", stroke="border")
    s = min(w, h) * 0.16
    _path(ctx, _pts([(x + w / 2 - s / 2, y + h / 2 - s), (x + w / 2 - s / 2, y + h / 2 + s), (x + w / 2 + s, y + h / 2)]) + " Z", fill="border")
    _frame_decor(n, x, y, w, h, ctx, [{"text": "LIVE", "tone": "solid-danger"}] if n.get("live") else [])
    return {"w": w, "h": h}


def _draw_heat(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    _rect(ctx, x, y, w, h, r=6, fill="code", stroke="border")
    base = min(w, h)
    probe = n.get("probe") or {}
    hx, hy = x + w * probe.get("x", 0.46), y + h * probe.get("y", 0.5)
    _circle(ctx, x + w * 0.2, y + h * 0.66, base * 0.16, fill="accent", op=0.15)
    for r, op in ((0.3, 0.12), (0.2, 0.25), (0.1, 0.5)):
        _circle(ctx, hx, hy, base * r, fill="danger", op=op)
    _line(ctx, hx - 14, hy, hx + 14, hy, stroke="text", sw=2)
    _line(ctx, hx, hy - 14, hx, hy + 14, stroke="text", sw=2)
    for i, op in enumerate((0.6, 0.45, 0.3, 0.2, 0.12)):
        _rect(ctx, x + w - 24, y + h * 0.2 + i * (h * 0.12), 12, h * 0.12, fill="danger" if i < 2 else "accent", op=op)
    max_label = probe.get("value", n.get("max"))
    if n.get("scale"):
        lo, hi = n["scale"]
        u = n.get("unit", "℃")
        top, bot = y + h * 0.2, y + h * 0.8

        def lab(v, yy):
            _text(ctx, f"{js_num(v)}{u}", x + w - 30, _mid(yy), fill="muted", anchor="end")

        lab(hi, top + 6)
        lab(js_round((lo + hi) * 5) / 10, (top + bot) / 2)
        lab(lo, bot - 6)
    if max_label:
        mw = _tw(ctx, max_label, S, 700) + 12
        pref = hx - 18 - mw if hx + 18 + mw > x + w - 32 else hx + 18
        lx = max(x + 6, min(pref, x + w - mw - 6))
        _rect(ctx, lx, hy - 32, mw, 22, r=4, fill="bg", stroke="danger")
        _text(ctx, max_label, lx + mw / 2, _mid(hy - 21), weight=700, fill="danger", anchor="middle")
    _frame_decor(n, x, y, w, h, ctx, [])
    return {"w": w, "h": h}


def _rng(seed: int) -> Callable[[], float]:
    """lib/wireframe.ts:631-639 rng(): a small xorshift-style generator, seeded once for
    pointcloud()'s scatter so the figure is the same every time. Ported with explicit
    32-bit masking (JS's `| 0` / `>>> 0` / Math.imul) for a bit-identical sequence."""
    state = seed & 0xFFFFFFFF

    def next_() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        a = state
        t = ((a ^ (a >> 15)) * (1 | a)) & 0xFFFFFFFF
        t2 = ((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF
        t = (((t + t2) & 0xFFFFFFFF) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return next_


def _draw_pointcloud(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    _rect(ctx, x, y, w, h, r=6, fill="code", stroke="border")
    rnd = _rng(7 + round(w) * 31 + round(h))
    count = max(60, min(260, round(w * h / 450)))
    for i in range(count):
        kind = i % 5
        if kind < 2:
            px, py = x + 12 + rnd() * (w - 24), y + h * 0.72 + (rnd() - 0.5) * h * 0.06
        elif kind == 2:
            px, py = x + w * 0.22 + (rnd() - 0.5) * w * 0.03, y + 14 + rnd() * h * 0.6
        else:
            a = rnd() * math.pi * 2
            rr = rnd()
            px, py = x + w * 0.62 + math.cos(a) * rr * w * 0.16, y + h * 0.5 + math.sin(a) * rr * h * 0.2
        _rect(ctx, px, py, 4, 4, fill="accent", op=0.35 + rnd() * 0.55)
    _frame_decor(n, x, y, w, h, ctx, [])
    return {"w": w, "h": h}


def _draw_chart(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    _rect(ctx, x, y, w, h, r=6, fill="bg", stroke="border")
    if n.get("label"):
        _text(ctx, n["label"], x + 10, y + 8 + S, weight=700)
    x0, x1 = x + 14, x + w - 14
    y0 = y + (34 if n.get("label") else 14)
    y1 = y + h - (32 if n.get("xLabels") else 14)
    for i in range(3):
        _line(ctx, x0, y0 + (y1 - y0) * i / 3, x1, y0 + (y1 - y0) * i / 3, stroke="border", sw=1.5, dash="4,4")
    _line(ctx, x0, y1, x1, y1, stroke="muted")
    vals = n.get("points") or [0.3, 0.35, 0.4, 0.45, 0.6, 0.8]

    def px(i):
        return x0 if len(vals) == 1 else x0 + i * (x1 - x0) / (len(vals) - 1)

    def py(v):
        return y1 - max(0.0, min(1.0, v)) * (y1 - y0)

    if n.get("threshold") is not None:
        _line(ctx, x0, py(n["threshold"]), x1, py(n["threshold"]), stroke="danger", sw=2, dash="6,4")
        if n.get("thresholdLabel"):
            lw = _tw(ctx, n["thresholdLabel"], S, 400) + 16
            _rect(ctx, x0 + 2, py(n["threshold"]) - 26, lw, 22, fill="bg")
            _text(ctx, n["thresholdLabel"], x0 + 10, py(n["threshold"]) - 10, fill="danger")
    if n.get("kind") == "bar":
        bw = max(6.0, (x1 - x0) / len(vals) * 0.55)
        for i, v in enumerate(vals):
            _rect(ctx, x0 + (x1 - x0) / len(vals) * (i + 0.5) - bw / 2, py(v), bw, y1 - py(v), fill="accent", op=0.8)
    else:
        _path(ctx, _pts([(px(i), py(v)) for i, v in enumerate(vals)]), stroke="accent", sw=3)
        for i, v in enumerate(vals):
            _circle(ctx, px(i), py(v), 7 if i == n.get("alertAt") else 4, fill="danger" if i == n.get("alertAt") else "accent")
    if n.get("xLabels"):
        _text(ctx, n["xLabels"][0], x0, y + h - 10, fill="muted")
        _text(ctx, n["xLabels"][-1], x1, y + h - 10, fill="muted", anchor="end")
    return {"w": w, "h": h}


def _draw_map_legend(items: list[dict], right: float, top: float, ctx: dict) -> None:
    lw = max(_tw(ctx, i["label"], S, 400) for i in items) + 44
    hh = len(items) * 24 + 8
    xx, yy = right - lw, top
    _rect(ctx, xx, yy, lw, hh, r=6, fill="bg", op=0.95, stroke="border", sw=1.5)
    for k, it in enumerate(items):
        cx, cy = xx + 18, yy + 16 + k * 24
        if it["kind"] == "alert":
            _path(ctx, _pts([(cx, cy - 7), (cx + 7, cy), (cx, cy + 7), (cx - 7, cy)]) + " Z", fill="danger")
        elif it["kind"] == "equip":
            _rect(ctx, cx - 6, cy - 6, 12, 12, r=2, fill="bg", stroke="text")
        else:
            _circle(ctx, cx, cy, 7 if it["kind"] == "site" else 6, fill="accent")
        _text(ctx, it["label"], xx + 34, _mid(cy))


def _draw_marker(m: dict, px: float, py: float, max_x: float, ctx: dict) -> None:
    """lib/wireframe.ts:578-609 drawMarker(). `id`/`shape`/`fov`/`heading` need
    wireframe-parts.ts's glyph()/fovSector()/headingArrow(), not ported (see module
    docstring) — a marker using them raises NotImplementedError."""
    kind = m.get("kind", "robot")
    if kind == "robot" and (m.get("fov") is not None or m.get("id") is not None or m.get("shape") is not None or m.get("heading") is not None):
        raise NotImplementedError("wireframe(): map marker fov/id/shape/heading need wireframe-parts.ts's robot glyph, not ported")
    r = 11 if m.get("inside") is not None else 9
    if kind == "robot":
        _circle(ctx, px, py, 9, fill="accent", stroke="bg", sw=3)
    elif kind == "site":
        r = 12
        _circle(ctx, px, py, 12, fill="accent", stroke="bg", sw=3)
    elif kind == "alert":
        _path(ctx, _pts([(px, py - 11), (px + 11, py), (px, py + 11), (px - 11, py)]) + " Z", fill="danger", stroke="bg", sw=2)
    else:
        _rect(ctx, px - 8, py - 8, 16, 16, r=3, fill="bg", stroke="danger" if m.get("tone") == "danger" else "text")
        r = 9
    if m.get("inside") is not None:
        _badge(ctx, px, py, m["inside"], aria=f"経路点 {m['inside']}")
    if m.get("label"):
        lw = _tw(ctx, m["label"], S, 700) + 8
        col = "danger" if kind == "alert" else "text"
        if m.get("side") in ("bottom", "top"):
            ly = _grid(py + r + 3 if m["side"] == "bottom" else py - r - 3 - 22)
            _rect(ctx, px - lw / 2, ly, lw, 22, r=4, fill="bg", op=0.92)
            _text(ctx, m["label"], px, _mid(ly + 11), weight=700, fill=col, anchor="middle")
        else:
            lx = px + r + 4
            if m.get("side") == "left" or lx + lw > max_x - 16:
                lx = px - r - 4 - lw
            ty = _grid(py - 11)
            _rect(ctx, lx, ty, lw, 22, r=4, fill="bg", op=0.92)
            _text(ctx, m["label"], lx + 4, _mid(ty + 11), weight=700, fill=col)
    if m.get("n") is not None:
        ctx["callouts"].append({"n": m["n"], "x": px + 14, "y": py - 14})


def _draw_map(n: dict, x: float, y: float, w: float, h: float, ctx: dict) -> dict:
    _rect(ctx, x, y, w, h, r=6, fill="code", stroke="border")
    top = 40 if (n.get("overlay") or n.get("overlayRight")) else 14
    bx, by, bw, bh = x + 14, y + top, w - 28, h - top - 14

    def f(fx, fy):
        return bx + fx * bw, by + fy * bh

    plan = n.get("plan", "floor")
    if plan == "floor":
        _rect(ctx, bx, by, bw, bh, fill="bg", stroke="muted")
        for a, b, c, d in ((0.38, 0, 0.38, 0.4), (0.38, 0.58, 0.38, 1), (0, 0.55, 0.38, 0.55), (0.38, 0.5, 1, 0.5)):
            p, q = f(a, b), f(c, d)
            _line(ctx, p[0], p[1], q[0], q[1], stroke="muted")
    elif plan == "site":
        for a, b, c, d in ((0.06, 0.14, 0.32, 0.42), (0.46, 0.08, 0.24, 0.32), (0.54, 0.5, 0.36, 0.38)):
            p = f(a, b)
            _rect(ctx, p[0], p[1], c * bw, d * bh, r=4, fill="bg", stroke="muted")
    if n.get("route") and len(n["route"]) > 1:
        _path(ctx, _pts([f(a, b) for a, b in n["route"]]), stroke="accent", sw=3, dash="8,5")
    for m in n.get("markers") or []:
        _draw_marker(m, *f(m["x"], m["y"]), x + w, ctx)
    if n.get("legend"):
        _draw_map_legend(n["legend"], x + w - 8, y + 8, ctx)
    _frame_decor(n, x, y, w, h, ctx, [])
    return {"w": w, "h": h}


_DRAW: dict[str, Callable[[dict, float, float, float, float, dict], dict]] = {
    "spacer": lambda n, x, y, w, h, ctx: {"w": w, "h": 8},
    "col": _draw_col,
    "row": _draw_row,
    "card": _draw_card,
    "text": _draw_text,
    "btn": _draw_btn,
    "chip": _draw_chip_node,
    "input": _draw_input,
    "select": _draw_select,
    "tabs": _draw_tabs,
    "appbar": _draw_appbar,
    "seek": _draw_seek,
    "kv": _draw_kv,
    "stat": _draw_stat,
    "list": _draw_list,
    "table": _draw_table,
    "alert": _draw_alert,
    "image": _draw_image,
    "video": _draw_video,
    "heat": _draw_heat,
    "pointcloud": _draw_pointcloud,
    "chart": _draw_chart,
    "map": _draw_map,
}


def _frame_decor(n: dict, x: float, y: float, w: float, h: float, ctx: dict, defaults: list[dict]) -> None:
    """lib/wireframe.ts:612-629 frameDecor(): overlay chips, label, stamp shared by visual widgets."""
    cx = x + 8
    for c in [*defaults, *[_chip_spec(c) for c in (n.get("overlay") or [])]]:
        cx += _draw_chip(ctx, c["text"], cx, y + 8, c.get("tone")) + 6
    rx = x + w - 8
    for c in reversed([_chip_spec(c) for c in (n.get("overlayRight") or [])]):
        cw = _chip_w(ctx, c["text"])
        rx -= cw
        _draw_chip(ctx, c["text"], rx, y + 8, c.get("tone"))
        rx -= 6
    if n.get("label") and n["t"] != "chart":
        lw = _tw(ctx, n["label"], S, 700) + 12
        ty = _grid(y + h - 30)
        _rect(ctx, x + 8, ty, lw, 22, r=4, fill="bg", op=0.92)
        _text(ctx, n["label"], x + 14, _mid(ty + 11), weight=700, fill="muted")
    if n.get("stamp"):
        sw = _tw(ctx, n["stamp"], S, 400) + 12
        ty = _grid(y + h - 30)
        _rect(ctx, x + w - 8 - sw, ty, sw, 22, r=4, fill="bg", op=0.92)
        _text(ctx, n["stamp"], x + w - 14, _mid(ty + 11), fill="muted", anchor="end")


# ---- screen frame, callouts, notes, legend ---------------------------------------------------
TITLE_H = 32


def _kids_of(v) -> list[dict]:
    if not v:
        return []
    return v if isinstance(v, list) else [v]


def _hide_under(ctx: dict, big_x: float, big_y: float, big_w: float, big_h: float) -> None:
    """lib/wireframe.ts:647-660 hideUnder(): what an overlay covers is not drawn."""

    def inside(x, y, w, h) -> bool:
        return x >= big_x and y >= big_y and x + w <= big_x + big_w and y + h <= big_y + big_h

    def keep(p: dict) -> bool:
        if p["k"] == "text":
            w = _tw(ctx, p["s"], p["size"], p["weight"])
            x0 = p["x"] - w / 2 if p.get("anchor") == "middle" else (p["x"] - w if p.get("anchor") == "end" else p["x"])
            return not (x0 < big_x + big_w and x0 + w > big_x and p["y"] - p["size"] < big_y + big_h and p["y"] + 4 > big_y)
        if p["k"] == "rect" or p["k"] == "pill":
            return not inside(p["x"], p["y"], p["w"], p["h"])
        if p["k"] == "circle":
            return not inside(p["cx"] - p["r"], p["cy"] - p["r"], 2 * p["r"], 2 * p["r"])
        if p["k"] == "badge":
            return not inside(p["cx"] - p["w"] / 2, p["cy"] - p["r"] - 3, p["w"], 2 * p["r"] + 3)
        return True

    ctx["prims"] = [p for p in ctx["prims"] if keep(p)]


def _draw_overlay(o: dict, ctx: dict, x: float, y: float, w: float, h: float) -> None:
    """lib/wireframe.ts:663-697 drawOverlay(): dialog (a dimmed screen with a centred
    card) and toast (a dark notice at the bottom right)."""
    if o["t"] == "toast":
        tone = _tone_of(o.get("tone"))
        lead = 28 if o.get("n") is not None else 0
        tw_ = _tw(ctx, o["text"], S, 700) + 32 + lead
        hh = 36
        tx, ty = x + w - 14 - tw_, y + h - 14 - hh
        _hide_under(ctx, tx, ty, tw_, hh)
        _rect(ctx, tx, ty, tw_, hh, r=6, fill="danger" if tone == "danger" else "text")
        _text(ctx, o["text"], tx + lead + (tw_ - lead) / 2, _mid(ty + hh / 2), weight=700, fill="bg", anchor="middle")
        if o.get("n") is not None:
            ctx["callouts"].append({"n": o["n"], "x": tx + 18, "y": ty + hh / 2})
        return
    if o["t"] != "dialog":
        raise ValueError(f'wireframe(): overlay must be wf.dialog or wf.toast, got "{o["t"]}"')
    dw = o.get("w", min(380, w - 48))
    pad = 16
    body = _wrap_t(ctx, o["body"], S, 400, dw - 2 * pad) if o.get("body") else []
    buttons = o.get("buttons") or []
    dh = pad + 24 + (8 + len(body) * _lh(S) if body else 0) + (16 + 32 if buttons else 0) + pad
    dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    _rect(ctx, x, y, w, h, fill="text", op=0.3)
    _hide_under(ctx, dx, dy, dw, dh)
    _rect(ctx, dx, dy, dw, dh, r=8, fill="bg", stroke="text", sw=2.5)
    _text(ctx, o["title"], dx + pad, dy + pad + T, size=T, weight=700)
    if body:
        _rect(ctx, dx + pad - 8, dy + pad + 24, dw - 2 * pad + 16, len(body) * _lh(S) + 16, fill="bg")
    for k, l in enumerate(body):
        _text(ctx, l, dx + pad, dy + pad + 24 + 8 + S + k * _lh(S))
    bx = dx + dw - pad
    for b in reversed(buttons):
        bw = _auto_w(b, ctx) or 0
        bx -= bw
        _place(b, bx, dy + dh - pad - 32, bw, 32, ctx)
        bx -= 8
    if o.get("n") is not None:
        ctx["callouts"].append({"n": o["n"], "x": dx + dw - 18, "y": dy + 18})


def _flush_callouts(ctx: dict) -> None:
    for c in ctx["callouts"]:
        ctx["all"].append({"n": c["n"], "x": c["x"], "y": c["y"]})
        _badge(ctx, c["x"], c["y"], c["n"], aria=f"注釈 {c['n']}")
    ctx["callouts"] = []


def _root_of(item: dict) -> dict:
    root = item["root"]
    if isinstance(root, list):
        return {"t": "col", "children": root, "pad": 8}
    if root["t"] == "col" and root.get("pad") is None:
        return {**root, "pad": 8}
    return root


def _d(v, default):
    """JS `v ?? default`: a dict built by passing through an absent field as an explicit
    None (as layout_wireframe()/layout_screens() do for optional WfScreen fields) must
    still fall back here — unlike dict.get(key, default), which only falls back when the
    key itself is missing, not when its value is None."""
    return default if v is None else v


def _inset_of(item: dict) -> float:
    return 0 if _d(item.get("frame"), "screen") == "none" else 3


def _fit_height(item: dict, ctx: dict, w: float) -> float:
    inset = _inset_of(item)
    return math.ceil(_nat(_root_of(item), w - 2 * inset, ctx)) + 2 * inset


def _layout_screen(item: dict, ctx: dict, x: float, y: float, w: float, default_h) -> dict:
    frame = _d(item.get("frame"), "screen")
    inset = _inset_of(item)
    hh = _d(item.get("h"), default_h)
    hv = _fit_height(item, ctx, w) if hh == "fit" else hh
    y0 = y
    if item.get("title"):
        _text(ctx, item["title"], x, y + 20, size=T, weight=700)
        if item.get("tag"):
            _draw_chip(ctx, item["tag"], x + _tw(ctx, item["title"], T, 700) + 10, y + 2, _d(item.get("tagTone"), "solid" if item["tag"] == "新規" else "accent"))
        y0 += TITLE_H
    ctx["skeleton"] = bool(item.get("skeleton"))
    if frame == "screen":
        _rect(ctx, x, y0, w, hv, r=4, fill="bg", stroke="text", sw=2.5)
    elif frame == "light":
        _rect(ctx, x, y0, w, hv, r=8, fill="bg", stroke="border", sw=2)
    _place(_root_of(item), x + inset, y0 + inset, w - 2 * inset, hv - 2 * inset, ctx)
    for o in _kids_of(item.get("overlays")):
        _draw_overlay(o, ctx, x + inset, y0 + inset, w - 2 * inset, hv - 2 * inset)
    _flush_callouts(ctx)
    return {"frame": {"x": x, "y": y0, "w": w, "h": hv}, "top": y, "bottom": y0 + hv}


def _na_of(c) -> str | None:
    return c.get("na") if isinstance(c, dict) and "na" in c else None


def _layout_matrix(band: dict, ctx: dict, x: float, y: float, w: float) -> dict:
    m = band["matrix"]
    n = len(m["cols"])
    label_w = m.get("labelW", 112)
    gap = m.get("gap", 12)
    cw = (w - label_w - gap * n) / n
    anchors: list[dict] = []
    cy = y
    for i, c in enumerate(m["cols"]):
        _text(ctx, c, x + label_w + gap + i * (cw + gap) + cw / 2, cy + 20, size=T, weight=700, anchor="middle")
    cy += 32
    for row in m["rows"]:
        if len(row["cells"]) > n:
            raise ValueError(f'stateMatrix(): row "{row["label"]}" has {len(row["cells"])} cells for {n} columns')
        cells = [row["cells"][i] if i < len(row["cells"]) else None for i in range(n)]
        nodes = [c for c in cells if isinstance(c, dict) and c.get("t")]
        rh = m.get("cellH")
        if rh is None:
            rh = max([72.0, *[math.ceil(_nat(nd, cw - 6, ctx)) + 6 for nd in nodes]])
        lab = _wrap_t(ctx, row["label"], T, 700, label_w - 8)
        note = _wrap_t(ctx, row["note"], S, 400, label_w - 8) if row.get("note") else []
        th = len(lab) * _lh(T) + (2 + len(note) * _lh(S) if note else 0)
        ty = cy + max(0.0, (rh - th) / 2)
        for k, l in enumerate(lab):
            _text(ctx, l, x, ty + T + k * _lh(T), size=T, weight=700)
        ty += len(lab) * _lh(T) + 2
        for k, l in enumerate(note):
            _text(ctx, l, x, ty + S + k * _lh(S), fill="muted")
        for i, cell in enumerate(cells):
            cx = x + label_w + gap + i * (cw + gap)
            na = _na_of(cell)
            if cell == "na" or na is not None:
                _rect(ctx, cx, cy, cw, rh, r=8, fill="code", stroke="border", sw=2, dash="6,4")
                _text(ctx, "対象外", cx + cw / 2, _mid(cy + rh / 2 - (10 if na else 0)), weight=700, fill="muted", anchor="middle")
                if na:
                    for k, l in enumerate(_wrap_t(ctx, na, S, 400, cw - 16)):
                        _text(ctx, l, cx + cw / 2, cy + rh / 2 + 10 + S * 0.36 + k * _lh(S), fill="muted", anchor="middle")
            elif cell is None or cell == "todo":
                _rect(ctx, cx, cy, cw, rh, r=8, fill="bg", stroke="danger", sw=2.5, dash="6,4")
                _text(ctx, "未設計", cx + cw / 2, _mid(cy + rh / 2), weight=700, fill="danger", anchor="middle")
            else:
                scr = _layout_screen({"root": cell, "h": rh, "frame": m.get("cellFrame", "light"), "skeleton": band.get("skeleton")}, ctx, cx, cy, cw, rh)
                anchors.append({"x": scr["frame"]["x"], "y": scr["top"], "w": scr["frame"]["w"], "h": scr["bottom"] - scr["top"]})
        cy += rh + 12
    return {"bottom": cy - 12, "anchors": anchors}


def _draw_marks_legend(ctx: dict, marks: dict | None, x: float, y: float) -> float:
    cx = x
    for k, default_label in (("new", "新規"), ("changed", "改修")):
        if k not in ctx["used"]:
            continue
        _rect(ctx, cx, y + 4, 28, 16, r=4, stroke="accent", sw=2.5, dash="6,4" if k == "new" else None)
        lab = (marks or {}).get(k, default_label)
        _text(ctx, lab, cx + 36, _mid(y + 12))
        cx += 36 + _tw(ctx, lab, S, 400) + 24
    return 28.0 if ctx["used"] else 0.0


def _draw_notes(ctx: dict, notes: list, x: float, y: float, w: float) -> float:
    cy = y
    for i, nt in enumerate(notes):
        o = {"text": nt} if isinstance(nt, str) else nt
        num = o.get("n", i + 1)
        tl = _wrap_t(ctx, o["title"], S, 700, w - 48) if o.get("title") else []
        bl = _wrap_t(ctx, o["text"], S, 400, w - 48) if o.get("text") else []
        _badge(ctx, x + 12, cy + 12, num, aria=f"注釈 {num}")
        ty = cy + 4
        for l in tl:
            _text(ctx, l, x + 36, ty + S, weight=700)
            ty += _lh(S)
        for l in bl:
            _text(ctx, l, x + 36, ty + S, fill="muted" if o.get("title") else "text")
            ty += _lh(S)
        cy = max(cy + 28, ty + 4) + 10
    return cy - 10 - y


def layout_wireframe(band: dict, x: float, y: float, w: float, width_of: WidthOf, wrap_mode: WrapMode) -> dict:
    """lib/wireframe.ts:796-806 layoutWireframe()."""
    ctx = _mk_ctx(width_of, wrap_mode, band.get("skeleton"))
    has_notes = bool(band.get("notes"))
    note_w = band.get("noteW", 264)
    gap = 28
    sw = w - note_w - gap if has_notes else w
    scr = _layout_screen({"title": band.get("title"), "tag": band.get("tag"), "tagTone": band.get("tagTone"), "root": band["root"], "overlays": band.get("overlays"), "h": band.get("h"), "frame": band.get("frame"), "skeleton": band.get("skeleton")}, ctx, x, y, sw, 440)
    bottom = scr["bottom"]
    if has_notes:
        bottom = max(bottom, scr["frame"]["y"] + _draw_notes(ctx, band["notes"], x + sw + gap, scr["frame"]["y"], note_w))
    bottom += 32 if _draw_marks_legend(ctx, band.get("marks"), x, bottom + 4) else 0
    return {"type": "wireframe", "id": band.get("id"), "title": band.get("title"), "x": x, "y": y, "w": w, "h": bottom - y, "prims": ctx["prims"], "callouts": ctx["all"], "anchors": [{"id": band["id"], **scr["frame"]}] if band.get("id") else []}


def layout_screens(band: dict, x: float, y: float, w: float, width_of: WidthOf, wrap_mode: WrapMode) -> dict:
    """lib/wireframe.ts:808-840 layoutScreens()."""
    ctx = _mk_ctx(width_of, wrap_mode, band.get("skeleton"))
    if band.get("matrix"):
        r = _layout_matrix(band, ctx, x, y, w)
        bottom = r["bottom"] + (32 if _draw_marks_legend(ctx, band.get("marks"), x, r["bottom"] + 4) else 0)
        rows = band["matrix"]["rows"]
        return {"type": "screens", "id": band.get("id"), "title": rows[0]["label"] if rows else None, "x": x, "y": y, "w": w, "h": bottom - y, "prims": ctx["prims"], "anchors": r["anchors"]}
    gap = band.get("gap", 64)
    row_gap = band.get("rowGap", 56)
    items = band["items"]
    explicit = any(it.get("at") for it in items)
    cols = band.get("cols")
    if cols is None:
        cols = max((math.ceil(it["at"][1] + 1) for it in items if it.get("at")), default=0) if explicit else 3
    cw = (w - (cols - 1) * gap) / cols
    cells = [{"it": it, "row": it["at"][0] if it.get("at") else i // cols, "col": it["at"][1] if it.get("at") else i % cols} for i, it in enumerate(items)]
    n_rows = max((c["row"] for c in cells), default=-1) + 1
    anchors: list[dict] = []
    cy = y
    for r in range(n_rows):
        row_bottom = cy
        in_row = [c for c in cells if c["row"] == r]
        fits = [_fit_height(c["it"], ctx, cw) for c in in_row if c["it"].get("h", band.get("h")) == "fit"]
        row_fit = max(fits) if fits else None
        for c in in_row:
            it, col = c["it"], c["col"]
            h_for_it = row_fit if it.get("h", band.get("h")) == "fit" else it.get("h")
            scr = _layout_screen({**it, "h": h_for_it, "skeleton": it.get("skeleton", band.get("skeleton"))}, ctx, x + col * (cw + gap), cy, cw, band.get("h", 320))
            if it.get("id"):
                anchors.append({"id": it["id"], "x": scr["frame"]["x"], "y": scr["top"], "w": scr["frame"]["w"], "h": scr["bottom"] - scr["top"]})
            row_bottom = max(row_bottom, scr["bottom"])
        cy = row_bottom + row_gap
    bottom = cy - row_gap
    bottom += 32 if _draw_marks_legend(ctx, band.get("marks"), x, bottom + 4) else 0
    return {"type": "screens", "id": band.get("id"), "title": items[0].get("title") if items else None, "x": x, "y": y, "w": w, "h": bottom - y, "prims": ctx["prims"], "anchors": anchors}


def render_prims(b: dict, day: int | str = 1) -> str:
    """lib/emit-tables.ts:109-136 renderPrims()."""

    def col(k: str | None) -> str:
        return "none" if k is None else color_of(k, day)

    def stroke(p: dict) -> str:
        dash = p.get("dash")  # circle prims never carry one
        if not p.get("stroke"):
            return ""
        return f' stroke="{col(p["stroke"])}" stroke-width="{js_num(p["sw"])}"' + (f' stroke-dasharray="{dash}"' if dash else "")

    def fill(p: dict) -> str:
        f = f'fill="{col(p.get("fill"))}"'
        if p.get("op") is not None and p.get("fill"):
            f += f' fill-opacity="{js_num(p["op"])}"'
        return f

    out: list[str] = []
    for p in b["prims"]:
        if p["k"] == "rect":
            x0, y0, x1, y1 = snap4(p["x"]), snap4(p["y"]), snap4(p["x"] + p["w"]), snap4(p["y"] + p["h"])
            rx_attr = f' rx="{p["r"]}"' if p["r"] else ""
            out.append(f'<rect x="{x0}" y="{y0}" width="{max(0, x1 - x0)}" height="{max(0, y1 - y0)}"{rx_attr} {fill(p)}{stroke(p)}/>')
        elif p["k"] == "circle":
            out.append(f'<circle cx="{snap4(p["cx"])}" cy="{snap4(p["cy"])}" r="{js_num(p["r"])}" {fill(p)}{stroke(p)}/>')
        elif p["k"] == "path":
            join_attr = ' stroke-linejoin="round"' if p.get("stroke") else ""
            out.append(f'<path d="{p["d"]}" {fill(p)}{stroke(p)}{join_attr}/>')
        elif p["k"] == "pill":
            x0, y0, x1, y1 = snap4(p["x"]), snap4(p["y"]), snap4(p["x"] + p["w"]), snap4(p["y"] + p["h"])
            out.append(pill_svg(x=x0, y=y0, w=max(0, x1 - x0), h=max(0, y1 - y0), fill=col(p["fill"]), stroke=col(p["stroke"]) if p.get("stroke") else None, cx=p["x"] + p["w"] / 2, baseline=p["base"], raw_y=p["y"], text=col(p["text"]), size=p["size"], label_html=emoji_span(p["label"])))
        elif p["k"] == "badge":
            out.append(badge_svg(cx=p["cx"], cy=p["cy"], r=p["r"], w=p["w"], shape=p["shape"], label=p["label"], aria=p["aria"], size=p["size"], fill=col(p["fill"]), stroke=PALETTE["bg"], sw=2, snap=snap4, esc=escape_xml))
        elif p["k"] == "text":
            a = ' text-anchor="middle"' if p.get("anchor") == "middle" else (' text-anchor="end"' if p.get("anchor") == "end" else "")
            out.append(f'<text x="{js_round(p["x"])}" y="{js_round(p["y"])}"{a} font-size="{js_num(p["size"])}" font-weight="{js_num(p["weight"])}" fill="{col(p["fill"])}">{emoji_span(p["s"])}</text>')
    return "\n  ".join(out)
