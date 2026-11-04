"""1:1 port of lib/seq-table.ts's layoutTable() (exported, golden-tested live) and
lib/emit-tables.ts's renderTable(). Icon cells (cellOf's `icon`/`iconGlyph`) are NOT
supported — same "defer icon(), it needs project-specific glyph data" boundary as box().

Golden master: lib/seq-table.ts + lib/emit-tables.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .atoms import WidthOf, split_atoms
from .emit_common import snap4
from .tokens import CELL_MARKS, PALETTE, resolve_box_style, text_color_of
from .wrap import WrapMode, wrap_atoms

LH = 1.4
TBL_PAD_X, TBL_PAD_Y, TBL_PAD_Y_DENSE = 12, 8, 4


def line_h(size: float) -> float:
    return size * LH


def _wrap(text: str, size: float, weight: int, max_w: float, width_of: WidthOf, mode: WrapMode) -> list[str]:
    return wrap_atoms(split_atoms(text), max_width=max(20, max_w), atom_width=lambda a: width_of(a, size, weight, "sans"), mode=mode)


def cell_of(cell, col: dict | None = None) -> dict:
    """lib/seq-table.ts:142-149 cellOf()."""
    col = col or {}
    if isinstance(cell, (str, int, float)) and not isinstance(cell, dict):
        c = {"text": str(cell)}
    else:
        c = dict(cell)
    mark_name = c.get("mark")
    mark = CELL_MARKS.get(mark_name) if mark_name else None
    if mark_name and not mark:
        raise ValueError(f'table cell: unknown mark "{mark_name}" (use {" | ".join(CELL_MARKS)})')
    if mark:
        text = f"{mark['glyph']} {c['text']}" if c.get("text") else mark["glyph"]
    else:
        text = c.get("text", "")
    out = {
        "text": text,
        "bold": c.get("bold", mark["bold"] if mark else col.get("bold", False)),
        "mono": c.get("mono", col.get("mono", False)),
        "align": c.get("align", col.get("align", "left")),
    }
    tone = c.get("tone") or (mark["tone"] if mark else None)
    if tone is not None:
        out["tone"] = tone
    if c.get("vAlign") is not None:
        out["vAlign"] = c["vAlign"]
    return out


def layout_table(*, columns: list[dict], rows: list, x: float, y: float, w: float, width_of: WidthOf, roles: dict, mode: WrapMode = "phrase", width: float | None = None, title: str | None = None, dense: bool = False, header: bool | None = None, row_header: bool = False, header_h: float | None = None, cell_h: float | None = None, row_curve: dict | None = None) -> dict:
    """lib/seq-table.ts:151-216 layoutTable()."""
    tw = min(w, width if width is not None else w)
    left = x + (w - tw) / 2
    flex_sum = sum(c.get("flex", 1) for c in columns)
    col_w = [tw * c.get("flex", 1) / flex_sum for c in columns]
    col_x = []
    ax = left
    for cw in col_w:
        col_x.append(ax)
        ax += cw

    pad_y = TBL_PAD_Y_DENSE if dense else TBL_PAD_Y
    cy = y
    title_bar = None
    if title:
        lines = _wrap(title, roles["title"], 700, tw - 2 * TBL_PAD_X, width_of, mode)
        h = len(lines) * line_h(roles["title"]) + 2 * TBL_PAD_Y
        title_bar = {"y": cy, "h": h, "lines": lines}
        cy += h

    laid_rows: list[dict] = []

    def row_of(cells: list, is_header: bool, tone: str | None = None, row_h: float | None = None, curve: bool = False) -> dict:
        nonlocal cy
        placed = []
        for i, cell in enumerate(cells):
            if is_header:
                c = {"text": cell.get("label", ""), "bold": True, "mono": False, "align": cell.get("align", "left")}
            else:
                c = cell_of(cell, columns[i] if i < len(columns) else None)
            if row_header and not is_header and i == 0:
                c["bold"] = True
            size = roles["body"]
            lines = [] if c["text"] == "" else _wrap(c["text"], size, 700 if c["bold"] else 400, col_w[i] - 2 * TBL_PAD_X, width_of, mode)
            placed.append({**c, "lines": lines, "x": col_x[i], "w": col_w[i], "top": 0})
        n_lines = max([1] + [len(c["lines"]) for c in placed])
        need = n_lines * line_h(roles["body"]) + 2 * pad_y
        fixed = row_h
        if fixed is None:
            fixed = header_h if is_header else None
        if fixed is None:
            fixed = cell_h
        if fixed is not None and fixed < need:
            import math

            label = "h" if row_h is not None else ("headerH" if is_header and header_h is not None else "cellH")
            raise ValueError(f"table(): {label} {fixed} is too small for a row that needs {math.ceil(need)}px ({n_lines} line(s) of {roles['body']}px text). Raise it or shorten the text")
        data_lines = max([0] + [len(c["lines"]) for c in placed[1:]])
        h = max(fixed if fixed is not None else need, (pad_y + data_lines * line_h(roles["body"]) + 8 + 30 + 10) if curve else 0)
        for c in placed:
            c["top"] = (cy + pad_y) if (fixed is None or c.get("vAlign") == "top") else (cy + (h - len(c["lines"]) * line_h(roles["body"])) / 2)
        row = {"y": cy, "h": h, "cells": placed, "header": is_header}
        if tone is not None:
            row["tone"] = tone
        cy += h
        return row

    has_header = any(c.get("label") for c in columns) and header is not False
    if has_header:
        laid_rows.append(row_of(columns, True))
    for i, r in enumerate(rows):
        cells = r["cells"] if isinstance(r, dict) and "cells" in r else r
        assert isinstance(cells, list)  # a row is a list of cells directly, or {cells: [...], ...}
        row_tone = r.get("tone") if isinstance(r, dict) and "cells" in r else None
        row_h_override = r.get("h") if isinstance(r, dict) and "cells" in r else None
        laid_rows.append(row_of(cells, False, row_tone, row_h_override, bool(row_curve) and row_curve.get("row") == i))

    laid_row_curve = None
    if row_curve:
        body = [r for r in laid_rows if not r["header"]]
        row = body[row_curve["row"]] if 0 <= row_curve["row"] < len(body) else None
        if row is None:
            raise ValueError(f"table(): rowCurve row {row_curve['row']} does not exist")
        if len(row_curve["values"]) != len(columns) - 1:
            raise ValueError(f"table(): rowCurve has {len(row_curve['values'])} values for {len(columns) - 1} data columns")
        text_bottom = max([row["y"]] + [c["top"] + len(c["lines"]) * line_h(roles["body"]) for c in row["cells"][1:]])
        top = max(row["y"] + row["h"] * 0.5, text_bottom + 8)
        bottom = row["y"] + row["h"] - 10
        span = row_curve["max"] - row_curve["min"]

        def y_of(v: float) -> float:
            return bottom - (v - row_curve["min"]) / span * (bottom - top)

        laid_row_curve = {
            "points": [{"x": col_x[i + 1] + col_w[i + 1] / 2, "y": y_of(v)} for i, v in enumerate(row_curve["values"])],
            "midY": y_of((row_curve["min"] + row_curve["max"]) / 2),
            "top": top, "bottom": bottom,
        }
    out = {"x": left, "y": y, "w": tw, "h": cy - y, "titleBar": title_bar, "rows": laid_rows, "colX": col_x, "colW": col_w, "rowHeader": row_header or None, "bodySize": roles["body"]}
    if laid_row_curve:
        out["rowCurve"] = laid_row_curve
    return out


def render_table(b: dict, day: int | str = 1, roles: dict | None = None) -> str:
    """lib/emit-tables.ts:49-103 renderTable() (icon cells not supported)."""
    from .emit_common import text_lines
    from .tokens import ROLES as DEFAULT_ROLES

    roles = roles or DEFAULT_ROLES

    def rr_path(x: float, y: float, w: float, h: float, tl: float = 0, tr: float = 0, br: float = 0, bl: float = 0) -> str:
        x_, y_, w_, h_ = round(x), round(y), round(w), round(h)
        return (
            f"M{x_ + tl},{y_} H{x_ + w_ - tr} {f'A{tr},{tr} 0 0 1 {x_ + w_},{y_ + tr}' if tr else ''} "
            f"V{y_ + h_ - br} {f'A{br},{br} 0 0 1 {x_ + w_ - br},{y_ + h_}' if br else ''} "
            f"H{x_ + bl} {f'A{bl},{bl} 0 0 1 {x_},{y_ + h_ - bl}' if bl else ''} "
            f"V{y_ + tl} {f'A{tl},{tl} 0 0 1 {x_ + tl},{y_}' if tl else ''} Z"
        )

    parts = []
    r = 8
    last = len(b["rows"]) - 1
    titled = bool(b.get("titleBar"))
    if titled:
        t = b["titleBar"]
        parts.append(f'<path d="{rr_path(b["x"], t["y"], b["w"], t["h"], tl=r, tr=r)}" fill="{PALETTE[day]["accent"]}"/>')
        parts.append(text_lines(t["lines"], x=b["x"] + 12, top=t["y"] + 8, size=roles["title"], weight=700, fill=PALETTE["bg"]))
    rows = b["rows"]
    for i, row in enumerate(rows):
        top = i == 0 and not titled
        bottom = i == last
        tl, tr = (r, r) if top else (0, 0)
        bl, br = (r, r) if bottom else (0, 0)
        if row.get("header"):
            fill = PALETTE[day]["soft"]
        elif row.get("tone"):
            fill = resolve_box_style(row["tone"], day)["fill"]
        else:
            fill = PALETTE["bg"]
        parts.append(f'<path d="{rr_path(b["x"], row["y"], b["w"], row["h"], tl=tl, tr=tr, br=br, bl=bl)}" fill="{fill}"/>')
        if b.get("rowHeader") and not row.get("header"):
            parts.append(f'<path d="{rr_path(b["x"], row["y"], b["colW"][0], row["h"], tl=tl, bl=bl)}" fill="{PALETTE[day]["soft"]}"/>')
        if i > 0 or titled:
            parts.append(f'<path d="M{round(b["x"])},{round(row["y"])} H{round(b["x"] + b["w"])}" stroke="{PALETTE["border"]}" stroke-width="2"/>')
    y0, y1 = rows[0]["y"], rows[last]["y"] + rows[last]["h"]
    for i in range(1, len(b["colX"])):
        parts.append(f'<path d="M{round(b["colX"][i])},{round(y0)} V{round(y1)}" stroke="{PALETTE["border"]}" stroke-width="2"/>')
    first_body = next((i for i, rr in enumerate(rows) if not rr.get("header")), -1)
    if b.get("rowHeader") and first_body >= 0:
        parts.append(f'<path d="M{round(b["colX"][1])},{round(rows[first_body]["y"])} V{round(y1)}" stroke="{PALETTE["text"]}" stroke-width="3"/>')
    rc = b.get("rowCurve")
    if rc and rc.get("points"):
        parts.append(f'<path d="M{snap4(b["colX"][1] + 8)},{snap4(rc["midY"])} H{snap4(b["x"] + b["w"] - 8)}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="1.5" stroke-dasharray="4,4"/>')
        if len(rc["points"]) > 1:
            pts = " ".join(f'{snap4(p["x"])},{snap4(p["y"])}' for p in rc["points"])
            parts.append(f'<polyline points="{pts}" fill="none" stroke="{PALETTE[day]["accent"]}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>')
        for p in rc["points"]:
            px, py = snap4(p["x"]), snap4(p["y"])
            parts.append(f'<path d="M{px - 4},{py} A4,4 0 1 0 {px + 4},{py} A4,4 0 1 0 {px - 4},{py}" fill="{PALETTE["bg"]}" stroke="{PALETTE[day]["accent"]}" stroke-width="2.5"/>')
    for row in rows:
        for c in row["cells"]:
            left = c["x"] + 12
            right = c["x"] + c["w"] - 12
            anchor = "middle" if c["align"] == "center" else ("end" if c["align"] == "right" else "start")
            tx = (left + right) / 2 if c["align"] == "center" else (right if c["align"] == "right" else left)
            if c["lines"]:
                parts.append(text_lines(c["lines"], x=tx, top=c["top"], size=b["bodySize"], weight=700 if c.get("bold") else 400, anchor=anchor, fill=text_color_of(c.get("tone"), day), mono=c.get("mono", False)))
    top, h = b["y"], b["h"]
    parts.append(f'<path d="{rr_path(b["x"], top, b["w"], h, tl=r, tr=r, br=r, bl=r)}" fill="none" stroke="{PALETTE["text"]}" stroke-width="2.5"/>')
    return "\n  ".join(parts)
