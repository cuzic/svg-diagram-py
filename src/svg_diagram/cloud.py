"""1:1 port of lib/toc.ts's layoutCloudBand() (exported, golden-tested live) and
lib/emit-figures.ts's renderCloud() — the TOC "evaporating cloud" / conflict-resolution
diagram. A closed-form 5-box layout, no auto-layout/crossing-reduction engine (unlike
cause()).

Golden master: lib/toc.ts + lib/emit-figures.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import text_width
from .emit_boxes import render_box_rect
from .emit_common import arrow_path, emoji_span, js_round, snap4
from .tokens import PALETTE, color_of, tone_style
from .tree_text import measure_node, node_runs
from .wrap import WrapMode, wrap_text

KEYS = ["a", "b", "c", "d", "d2"]
LETTER = {"a": "A", "b": "B", "c": "C", "d": "D", "d2": "D'"}
ARROWS = ["ab", "ac", "bd", "cd", "dd"]
CLOUD_W, CLOUD_GAP_MIN, CLOUD_GAP_MAX, ROW_GAP, LIST_GAP, NUM_GAP = 220, 110, 170, 96, 28, 8


def _box_text(k: str, v) -> str:
    text = v if isinstance(v, str) else v["text"]
    return f"{LETTER[k]}：{text}"


def _injection_text(t: str) -> str:
    return f"→ {t}"


def _numbering(assumptions: list[dict]) -> tuple[dict, list[int]]:
    by: dict[str, list[int]] = {}
    for i, a in enumerate(assumptions):
        by.setdefault(a["on"], []).append(i + 1)
    chip = {k: ",".join(str(n) for n in v) for k, v in by.items()}
    return chip, [i + 1 for i in range(len(assumptions))]


def layout_cloud_band(*, boxes: dict, x: float, y: float, w: float, width_of, roles: dict, wrap_mode: WrapMode = "phrase", max_node_w: float | None = None, assumptions: list[dict] | None = None, conflict_label: str | None = None) -> dict:
    """lib/toc.ts:365-449 layoutCloudBand()."""
    assumptions = assumptions or []
    s = roles["note"]
    max_w = max_node_w if max_node_w is not None else CLOUD_W
    ids: set[str] = set()
    for k in KEYS:
        v = boxes[k]
        text = v if isinstance(v, str) else v.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"cloud(): box {LETTER[k]} needs a text")
        box_id = None if isinstance(v, str) else v.get("id")
        if box_id is not None:
            if box_id in ids:
                raise ValueError(f'cloud(): duplicate box id "{box_id}"')
            ids.add(box_id)
    for a in assumptions:
        if a["on"] not in ARROWS:
            raise ValueError(f"cloud(): an assumption sits on {', '.join(repr(k) for k in ARROWS)} (got {a['on']!r})")
        if not isinstance(a.get("text"), str) or not a["text"].strip():
            raise ValueError("cloud(): every assumption needs a text")

    col_w = min(max_w, math.floor((w - 2 * CLOUD_GAP_MIN) / 3))
    if col_w < 120:
        raise ValueError(f"cloud(): the figure has {round(w)}px, too narrow for five boxes and the arrows between them (needs {3 * 120 + 2 * CLOUD_GAP_MIN}px)")
    lines = {k: measure_node(_box_text(k, boxes[k]), None, col_w, width_of, roles, wrap_mode, False, keep_words=False) for k in KEYS}
    box_w = max(lines[k]["w"] for k in KEYS)
    h = max(lines["b"]["h"], lines["c"]["h"], lines["d"]["h"], lines["d2"]["h"])
    h_a = lines["a"]["h"]
    gap = min(CLOUD_GAP_MAX, math.floor((w - 3 * box_w) / 2))
    fig_w = 3 * box_w + 2 * gap
    rows_h = 2 * h + ROW_GAP
    fig_h = max(rows_h, h_a)
    top = (fig_h - rows_h) / 2
    x0 = x + (w - fig_w) / 2
    x1 = x0 + box_w + gap
    x2 = x1 + box_w + gap
    at = {
        "a": {"x": x0, "y": y + fig_h / 2 - h_a / 2, "w": box_w, "h": h_a},
        "b": {"x": x1, "y": y + top, "w": box_w, "h": h},
        "c": {"x": x1, "y": y + top + h + ROW_GAP, "w": box_w, "h": h},
        "d": {"x": x2, "y": y + top, "w": box_w, "h": h},
        "d2": {"x": x2, "y": y + top + h + ROW_GAP, "w": box_w, "h": h},
    }
    default_tone = {"a": "accent", "b": "plain", "c": "plain", "d": "plain", "d2": "plain"}
    out = {"x": x, "y": y, "w": w, "h": fig_h, "nodes": [], "edges": [], "chips": [], "texts": [], "anchors": [], "labelBoxes": []}
    for k in KEYS:
        v = boxes[k]
        r = at[k]
        node = {**r, "key": k, "tone": (None if isinstance(v, str) else v.get("tone")) or default_tone[k]}
        box_id = None if isinstance(v, str) else v.get("id")
        if box_id:
            node["id"] = box_id
        out["nodes"].append(node)
        if box_id:
            out["anchors"].append({"id": box_id, **r})
        out["texts"].extend(node_runs(r, lines[k], roles))
        out["labelBoxes"].append({"label": _box_text(k, v), **r})

    cy_b, cy_c, cy_a = at["b"]["y"] + h / 2, at["c"]["y"] + h / 2, at["a"]["y"] + h_a / 2
    off = min(12, h_a / 2 - 8)
    mid_x = at["a"]["x"] + box_w + gap / 2

    def edge(arrow: str, points: list[dict]) -> None:
        out["edges"].append({"arrow": arrow, "points": points})

    edge("ab", [{"x": x1, "y": cy_b}, {"x": mid_x, "y": cy_b}, {"x": mid_x, "y": cy_a - off}, {"x": x0 + box_w, "y": cy_a - off}])
    edge("ac", [{"x": x1, "y": cy_c}, {"x": mid_x, "y": cy_c}, {"x": mid_x, "y": cy_a + off}, {"x": x0 + box_w, "y": cy_a + off}])
    edge("bd", [{"x": x2, "y": cy_b}, {"x": x1 + box_w, "y": cy_b}])
    edge("cd", [{"x": x2, "y": cy_c}, {"x": x1 + box_w, "y": cy_c}])
    cx = x2 + box_w / 2
    y0 = y + top + h
    edge("dd", [{"x": cx, "y": y0}, {"x": cx, "y": y0 + ROW_GAP * 0.3}, {"x": cx + 10, "y": y0 + ROW_GAP * 0.45}, {"x": cx - 10, "y": y0 + ROW_GAP * 0.55}, {"x": cx, "y": y0 + ROW_GAP * 0.7}, {"x": cx, "y": y0 + ROW_GAP}])

    chip_map, numbers = _numbering(assumptions)
    chip_h = s + 8
    chip_at = {
        "ab": {"x": mid_x, "y": (cy_b + cy_a - off) / 2}, "ac": {"x": mid_x, "y": (cy_c + cy_a + off) / 2},
        "bd": {"x": (x1 + box_w + x2) / 2, "y": cy_b}, "cd": {"x": (x1 + box_w + x2) / 2, "y": cy_c}, "dd": {"x": 0, "y": y0 + ROW_GAP / 2},
    }

    def width_of_chip(text: str) -> float:
        return math.ceil(text_width(width_of, text, s, 400)) + 12

    def chip(arrow: str, text: str, cxm: float, cym: float, conflict: bool = False) -> None:
        cw = width_of_chip(text)
        entry = {"text": text, "x": cxm - cw / 2, "y": cym - chip_h / 2, "w": cw, "h": chip_h, "tx": cxm, "ty": cym - chip_h / 2 + s + 2, "size": s, "arrow": arrow}
        if conflict:
            entry["conflict"] = True
        out["chips"].append(entry)

    for arrow in ARROWS:
        text = chip_map.get(arrow)
        if not text:
            continue
        if arrow == "dd":
            cw = width_of_chip(text)
            right = cx + 22 + cw / 2
            left = right + cw / 2 > x + w
            chip(arrow, text, (cx - 22 - cw / 2) if left else right, chip_at["dd"]["y"] + (chip_h / 2 + 2 if (left and conflict_label) else 0))
        else:
            chip(arrow, text, chip_at[arrow]["x"], chip_at[arrow]["y"])
    if conflict_label:
        cw = width_of_chip(conflict_label)
        dd_text = chip_map.get("dd")
        offset = chip_h / 2 + 2 if (dd_text and cx + 22 + width_of_chip(dd_text) > x + w) else 0
        chip("dd", conflict_label, cx - 22 - cw / 2, chip_at["dd"]["y"] - offset, True)

    if assumptions:
        num_w = math.ceil(max(text_width(width_of, f"{i}.", s, 400) for i in numbers)) + NUM_GAP
        inner = fig_w - num_w
        lh = js_round(s * 1.4)

        def wrap(t: str) -> list[str]:
            return wrap_text(t, max_width=inner, atom_width=lambda a: width_of(a, s, 400, "sans"), mode=wrap_mode)

        ty = y + fig_h + LIST_GAP
        for i, a in enumerate(assumptions):
            out["texts"].append({"text": f"{i + 1}.", "x": x0, "y": ty + s, "size": s, "bold": False, "muted": False, "anchor": "start"})
            parts: list[tuple[str, str | None]] = [(a["text"], None)]
            if a.get("injection"):
                parts.append((_injection_text(a["injection"]), "accent"))
            for text, tone in parts:
                for line in wrap(text):
                    entry = {"text": line, "x": x0 + num_w, "y": ty + s, "size": s, "bold": False, "muted": False, "anchor": "start"}
                    if tone:
                        entry["tone"] = tone
                    out["texts"].append(entry)
                    ty += lh
            ty += 6
        out["h"] = ty - 6 - y
    return out


def render_cloud(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:361-378 renderCloud()."""
    dim = bool(b.get("dim"))
    stroke = PALETTE["muted"] if dim else PALETTE["text"]
    conflict = PALETTE["muted"] if dim else color_of("danger", day)
    accent = PALETTE["muted"] if dim else color_of("accent", day)

    out = []
    for e in b["edges"]:
        if e["arrow"] == "dd":
            out.append(arrow_path(e["points"], conflict, None, 2.5, "both"))
        else:
            out.append(arrow_path(e["points"], stroke, None))
    for n in b["nodes"]:
        out.append(render_box_rect(x=n["x"], y=n["y"], w=n["w"], h=n["h"], tone=n.get("tone"), dim=dim, default_tone="plain"))

    def ink(t: dict) -> str:
        if dim:
            return PALETTE["muted"]
        if t.get("tone"):
            return conflict if t["tone"] == "danger" else accent
        node = next((r for r in b["nodes"] if t["x"] >= r["x"] and t["x"] <= r["x"] + r["w"] and t["y"] > r["y"] and t["y"] <= r["y"] + r["h"]), None)
        return color_of(tone_style(node["tone"]).text, day) if node else PALETTE["text"]

    for t in b["texts"]:
        anchor = t.get("anchor", "middle")
        bold_attr = ' font-weight="700"' if t.get("bold") else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}" text-anchor="{anchor}" font-size="{t["size"]}"{bold_attr} fill="{ink(t)}">{emoji_span(t["text"])}</text>')
    for c in b["chips"]:
        out.append(f'<rect x="{snap4(c["x"])}" y="{snap4(c["y"])}" width="{snap4(c["w"])}" height="{c["h"]}" fill="{PALETTE["bg"]}"/>')
        fill = conflict if (c["arrow"] == "dd" or c.get("conflict")) else stroke
        out.append(f'<text x="{js_round(c["tx"])}" y="{js_round(c["ty"])}" text-anchor="middle" font-size="{c["size"]}" fill="{fill}">{emoji_span(c["text"])}</text>')
    return "\n  ".join(out)
