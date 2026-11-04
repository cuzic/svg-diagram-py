"""1:1 port of lib/seq-table.ts's prepareSequence()/layoutSequence() (exported, golden-
tested live) and lib/emit-tables.ts's renderSequence(). Actor icons are NOT supported —
same "defer icon(), needs project-specific glyph data" boundary as box().

Golden master: lib/seq-table.ts + lib/emit-tables.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .atoms import WidthOf, split_atoms, text_width
from .emit_common import snap4
from .tokens import PALETTE, resolve_box_style, text_color_of
from .wrap import WrapMode, wrap_atoms

LH = 1.4
SEQ_HEAD_PAD_Y, SEQ_HEAD_PAD_X, SEQ_STEP_GAP, SEQ_LABEL_GAP, SEQ_SELF_W, SEQ_DIVIDER_H = 12, 12, 14, 10, 36, 36


def line_h(size: float) -> float:
    return size * LH


def _wrap(text: str, size: float, weight: int, max_w: float, width_of: WidthOf, mode: WrapMode) -> list[str]:
    return wrap_atoms(split_atoms(text), max_width=max(20, max_w), atom_width=lambda a: width_of(a, size, weight, "sans"), mode=mode)


def _text_w(text: str, size: float, weight: int, width_of: WidthOf) -> float:
    return text_width(width_of, text, size, weight, "sans")


def prepare_sequence(actors: list[dict], steps: list[dict], numbered: bool = True) -> list[dict]:
    """lib/seq-table.ts:24-34 prepareSequence()."""
    n = 0
    out = []
    for s in steps:
        if s.get("divider") is not None:
            out.append({**s, "kind": "divider", "text": s["divider"]})
            continue
        if s.get("note") is not None:
            over = s["over"] if isinstance(s.get("over"), list) else [s.get("over")]
            out.append({**s, "kind": "note", "text": s["note"], "over": over})
            continue
        is_numbered = numbered is not False and s.get("number") is not False
        if is_numbered:
            n += 1
            text = f"{n}. {s['label']}"
        else:
            text = s["label"]
        kind = "self" if s.get("self") is not None else "msg"
        out.append({**s, "kind": kind, "text": text})
    return out


def layout_sequence(*, actors: list[dict], steps: list[dict], x: float, y: float, w: float, width_of: WidthOf, roles: dict, mode: WrapMode = "phrase", numbered: bool = True) -> dict:
    """lib/seq-table.ts:59-135 layoutSequence()."""
    prepared_steps = prepare_sequence(actors, steps, numbered)
    n = len(actors)
    col_w = w / n
    aw = min(200, col_w - 16)
    cx = [x + col_w * (i + 0.5) for i in range(n)]
    idx = {a["id"]: i for i, a in enumerate(actors)}

    def at(actor_id: str, what: str) -> int:
        if actor_id not in idx:
            raise ValueError(f'sequence(): unknown actor "{actor_id}" in {what}')
        return idx[actor_id]

    heads = []
    for i, a in enumerate(actors):
        lines = _wrap(a["label"], roles["title"], 700, aw - 2 * SEQ_HEAD_PAD_X, width_of, mode)
        ci = cx[i]
        head = {"id": a["id"], "lines": lines, "x": ci - aw / 2, "w": aw, "cx": ci, "y": 0, "h": 0, "textDy": SEQ_HEAD_PAD_Y}
        if a.get("tone") is not None:
            head["tone"] = a["tone"]
        heads.append(head)

    text_h = max(len(h["lines"]) for h in heads) * line_h(roles["title"])
    head_h = text_h + 2 * SEQ_HEAD_PAD_Y
    for h in heads:
        h["y"], h["h"] = y, head_h
        h["textDy"] = SEQ_HEAD_PAD_Y

    cursor = y + head_h
    laid_steps = []
    for s in prepared_steps:
        top = cursor + SEQ_STEP_GAP / 2
        if s["kind"] == "msg":
            i, j = at(s["from"], "from"), at(s["to"], "to")
            if i == j:
                raise ValueError(f'sequence(): message "{s["label"]}" has from === to; use {{self: id}}')
            span = abs(cx[j] - cx[i])
            mid = (cx[i] + cx[j]) / 2
            room = min(2 * (mid - x), 2 * (x + w - mid)) - 8
            lines = _wrap(s["text"], roles["note"], 400, min(room, max(span - 20, 320)), width_of, mode)
            label_h = len(lines) * line_h(roles["note"])
            ay = top + label_h + SEQ_LABEL_GAP
            step = {"kind": "msg", "x1": cx[i], "x2": cx[j], "y": ay, "lines": lines, "labelTop": top, "lx": (cx[i] + cx[j]) / 2, "line": s.get("line", "solid"), "arrow": s.get("arrow", "end")}
            if s.get("tone") is not None:
                step["tone"] = s["tone"]
            laid_steps.append(step)
            cursor = ay + SEQ_STEP_GAP
        elif s["kind"] == "self":
            i = at(s["self"], "self")
            ci = cx[i]
            right_room = x + w - (ci + SEQ_SELF_W + 8) - 4
            left_room = ci - SEQ_SELF_W - 8 - x - 4
            side = "left" if (_text_w(s["text"], roles["note"], 400, width_of) > right_room and left_room > right_room) else "right"
            lx = ci - SEQ_SELF_W - 8 if side == "left" else ci + SEQ_SELF_W + 8
            lines = _wrap(s["text"], roles["note"], 400, max(40, left_room if side == "left" else right_room), width_of, mode)
            label_h = len(lines) * line_h(roles["note"])
            loop_h = 22
            row_h = max(label_h, loop_h + 12)
            step = {"kind": "self", "cx": ci, "y": top + 6, "loopH": loop_h, "lines": lines, "lx": lx, "side": side, "labelTop": top, "line": s.get("line", "solid")}
            if s.get("tone") is not None:
                step["tone"] = s["tone"]
            laid_steps.append(step)
            cursor = top + row_h + SEQ_STEP_GAP / 2
        elif s["kind"] == "note":
            ids = [at(oid, "note.over") for oid in s["over"]]
            lo, hi = min(ids), max(ids)
            if lo == hi:
                nw = min(aw + 40, 260)
                left, right = cx[lo] - nw / 2, cx[lo] + nw / 2
            else:
                left, right = max(x, cx[lo] - 60), min(x + w, cx[hi] + 60)
            lines = _wrap(s["text"], roles["note"], 400, right - left - 24, width_of, mode)
            h = len(lines) * line_h(roles["note"]) + 16
            laid_steps.append({"kind": "note", "x": left, "y": top, "w": right - left, "h": h, "lines": lines, "tone": s.get("tone", "muted")})
            cursor = top + h + SEQ_STEP_GAP / 2
        else:  # divider
            tw = _text_w(s["text"], roles["note"], 700, width_of) + 24
            laid_steps.append({"kind": "divider", "y": top + 14, "x1": x, "x2": x + w, "cx": x + w / 2, "chipW": tw, "text": s["text"]})
            cursor = top + SEQ_DIVIDER_H - SEQ_STEP_GAP / 2

    bottom = cursor + 4
    return {"x": x, "y": y, "w": w, "h": bottom - y, "heads": heads, "steps": laid_steps, "lifeTop": y + head_h, "lifeBottom": bottom}


def render_sequence(b: dict, day: int | str = 1, roles: dict | None = None) -> str:
    """lib/emit-tables.ts:13-46 renderSequence()."""
    from .emit_common import stroke_line, text_lines
    from .tokens import ROLES as DEFAULT_ROLES

    roles = roles or DEFAULT_ROLES
    parts = []
    for h in b["heads"]:
        parts.append(f'<path d="M{round(h["cx"])},{round(h["y"] + h["h"])} L{round(h["cx"])},{round(b["lifeBottom"])}" fill="none" stroke="{PALETTE["border"]}" stroke-width="2" stroke-dasharray="6,6"/>')
    for h in b["heads"]:
        st = resolve_box_style(h.get("tone") or "plain", day)
        dash = ' stroke-dasharray="6,4"' if st["dashed"] else ""
        parts.append(f'<rect x="{snap4(h["x"])}" y="{snap4(h["y"])}" width="{snap4(h["w"])}" height="{snap4(h["h"])}" rx="8" fill="{st["fill"]}" stroke="{st["stroke"]}" stroke-width="2.5"{dash}/>')
        parts.append(text_lines(h["lines"], x=h["cx"], top=h["y"] + h["textDy"], size=roles["title"], weight=700, anchor="middle", fill=PALETTE["text"]))
    for s in b["steps"]:
        if s["kind"] == "msg":
            color = text_color_of(s.get("tone"), day)
            d = f'M{round(s["x1"])},{round(s["y"])} L{round(s["x2"])},{round(s["y"])}'
            parts.append(stroke_line(d, color, s.get("line"), s.get("arrow", "end")))
            parts.append(text_lines(s["lines"], x=s["lx"], top=s["labelTop"], size=roles["note"], anchor="middle", fill=color if s.get("tone") else PALETTE["text"]))
        elif s["kind"] == "self":
            color = text_color_of(s.get("tone"), day)
            direction = -1 if s["side"] == "left" else 1
            x0, x1_ = round(s["cx"]), round(s["cx"] + direction * 36)
            y0, y1_ = round(s["y"]), round(s["y"] + s["loopH"])
            d = f"M{x0},{y0} L{x1_},{y0} L{x1_},{y1_} L{x0},{y1_}"
            parts.append(stroke_line(d, color, s.get("line"), "end"))
            anchor = "end" if s["side"] == "left" else "start"
            parts.append(text_lines(s["lines"], x=s["lx"], top=s["labelTop"], size=roles["note"], anchor=anchor, fill=color if s.get("tone") else PALETTE["text"]))
        elif s["kind"] == "note":
            st = resolve_box_style(s.get("tone"), day)
            dash = ' stroke-dasharray="6,4"' if st["dashed"] else ""
            parts.append(f'<rect x="{snap4(s["x"])}" y="{snap4(s["y"])}" width="{snap4(s["w"])}" height="{snap4(s["h"])}" rx="8" fill="{st["fill"]}" stroke="{st["stroke"]}" stroke-width="2.5"{dash}/>')
            parts.append(text_lines(s["lines"], x=s["x"] + 12, top=s["y"] + 8, size=roles["note"], fill=PALETTE["text"]))
        else:
            parts.append(f'<path d="M{round(s["x1"])},{round(s["y"])} L{round(s["x2"])},{round(s["y"])}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="2" stroke-dasharray="6,4"/>')
            parts.append(f'<rect x="{snap4(s["cx"] - s["chipW"] / 2)}" y="{snap4(s["y"] - 12)}" width="{snap4(s["chipW"])}" height="24" rx="12" fill="{PALETTE["bg"]}" stroke="{PALETTE["muted"]}" stroke-width="2"/>')
            parts.append(text_lines([s["text"]], x=s["cx"], top=s["y"] - 12 + 1, size=roles["note"], weight=700, anchor="middle", fill=PALETTE["text"]))
    return "\n  ".join(parts)
