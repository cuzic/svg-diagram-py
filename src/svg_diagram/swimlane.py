"""1:1 port of lib/swimlane.ts's layoutSwimlaneBand() (exported, golden-tested live) and
lib/emit-boxes.ts's renderSwimlane() + renderBox() (each step renders as a plain box).

Scope, matching this port's other closed-form bands (tree()/gantt()/table()/...):
connect()-ability (an id on a step reachable from another band via connect()) is NOT
supported, since this port has no shared anchor registry — same boundary as
connect()'s weight: 'strong' / line: 'double'. `opts.flows` and `opts.laneOrder` (both
built on that registry — flows become connect() bands, laneOrder reorders lanes to
shorten them) are therefore out of scope too, as is the DSL-level `swimlane()` builder
itself (callers pass an already-placed band: each step already carries its `col`/`span`,
same convention as gantt()/table()/tree()). A step's `icon` is out of scope project-wide
(see model.py's Box); step badges on anything but a left-aligned title share the
left-aligned-only restriction already documented on render_step_badge().

Golden master: lib/swimlane.ts + lib/emit-boxes.ts's renderSwimlane()/renderBox() (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import WidthOf, split_atoms, text_width
from .emit_boxes import render_box_rect, render_stamp, render_step_badge, render_tag
from .emit_common import emoji_span, js_num, js_round
from .layout_util import (
    BOX_INNER_GAP,
    BOX_PAD_X,
    BOX_PAD_Y,
    LINE_HEIGHT_EM,
    STAMP_GAP,
    STAMP_H,
    STEP_INDENT,
    SWIMLANE_COMFY_COL,
    TAG_H,
    TAG_PAD_X,
    boundary_chip_h,
    snap_grid,
    stamp_chip_w,
)
from .tokens import PALETTE, TAG_SIZE, is_solid_tone, run_color_of
from .wrap import WrapMode, wrap_atoms


def _wrap_lines(text: str, size: float, weight: int, max_w: float, width_of: WidthOf, mode: WrapMode) -> list[str]:
    return wrap_atoms(split_atoms(text), max_width=max(20, max_w), atom_width=lambda a: width_of(a, size, weight, "sans"), mode=mode)


def _narrow_texts(texts: list[list[str]]) -> list[str]:
    """lib/tree.ts:38 narrowTexts(): the wrapped texts that broke into lines of 2.5
    characters or fewer on average (what fit: 'shrink' squeezing a column too far does)."""
    out: list[str] = []
    for lines in texts:
        if len(lines) < 3:
            continue
        joined = "".join(lines)
        if len(joined.replace(" ", "").replace("　", "")) / len(lines) > 2.5:
            continue
        if joined not in out:
            out.append(joined)
    return out


def _text_runs(step: dict, roles: dict) -> list[dict]:
    """lib/layout-text.ts's boxRuns(), restricted to title/body/lines/note (no icon
    indent — icon is out of scope project-wide; no spans). Only the title run shifts
    for a step() badge; body/lines/note only shift for an icon (never, here)."""

    def tone_field(tone: str | None) -> dict:
        return {"tone": tone} if tone is not None else {}

    # body/lines/note have NO "indent" key at all here (Node only sets one when there's
    # an icon — unsupported project-wide, see above); only the title run always has one.
    runs: list[dict] = []
    if step.get("title"):
        indent = STEP_INDENT if step.get("step") is not None else 0
        runs.append({"text": step["title"], "size": roles["title"], "weight": 700, "mono": bool(step.get("titleMono")), **tone_field(step.get("titleTone")), "indent": indent})
    if step.get("body"):
        runs.append({"text": step["body"], "size": roles["body"], "weight": 400, "mono": bool(step.get("bodyMono")), **tone_field(step.get("bodyTone"))})
    for line in step.get("lines") or []:
        spec = {"text": line} if isinstance(line, str) else line
        size = roles.get(spec.get("role", "body"), roles["body"])
        runs.append({"text": spec["text"], "size": size, "weight": 700 if spec.get("bold") else 400, "mono": bool(spec.get("mono")), **tone_field(spec.get("tone")), "nowrap": False})
    if step.get("note"):
        note_tone = step.get("noteTone")
        if note_tone is None and not is_solid_tone(step.get("tone")):
            note_tone = "muted"
        runs.append({"text": step["note"], "size": roles["note"], "weight": 400, "mono": False, **tone_field(note_tone)})
    return runs


def _layout_box_content(step: dict, wrap_width: float, width_of: WidthOf, roles: dict, mode: WrapMode) -> tuple[list[dict], float]:
    """lib/layout-text.ts's layoutBoxContent(), without fit/nowrap/spans (box({stat}) and
    rich spans are out of scope for swimlane steps)."""
    rel_y = 0.0
    wrapped_runs: list[dict] = []
    for run in _text_runs(step, roles):
        indent = run.get("indent", 0)
        lines = _wrap_lines(run["text"], run["size"], run["weight"], wrap_width - indent, width_of, mode)
        line_ys = []
        for _ in lines:
            rel_y += run["size"]
            line_ys.append(rel_y)
            rel_y += run["size"] * (LINE_HEIGHT_EM - 1)
        rel_y += BOX_INNER_GAP
        wrapped_runs.append({**run, "lines": lines, "lineYs": line_ys})
    text_height = max(0.0, rel_y - BOX_INNER_GAP)
    return wrapped_runs, text_height


def _measure_box_like(step: dict, x: float, y0: float, w: float, width_of: WidthOf, roles: dict, mode: WrapMode) -> dict:
    """lib/layout.ts's measureBoxLike(), restricted to isBoxLike=True (swimlane steps
    only) with the icon/leftIcon shift always zero (icon is out of scope project-wide,
    same boundary as model.py's Box)."""
    y = snap_grid(y0)
    pad_x = step.get("padX", BOX_PAD_X)
    pad_y = step.get("padY", BOX_PAD_Y)
    wrap_width = w - 2 * pad_x
    wrapped_runs, text_height = _layout_box_content(step, wrap_width, width_of, roles, mode)
    stamp = step.get("stamp")
    stamp_w = stamp_chip_w(width_of, stamp, roles["note"]) if stamp else None
    if stamp_w is not None and stamp_w > w - 16:
        raise ValueError(f'stamp "{stamp}" is wider than its box ({round(w)}px): shorten it or widen the box')
    h = text_height + 2 * pad_y + (STAMP_H + STAMP_GAP if stamp else 0)
    placed = {**step, "x": x, "y": y, "w": w, "h": h, "wrappedRuns": wrapped_runs}
    if stamp_w is not None:
        placed["stampW"] = stamp_w
    align = step.get("align", "left")
    if step.get("step") is not None and step.get("title") and align != "left" and wrapped_runs:
        title_run = wrapped_runs[0]
        placed["titleW"] = text_width(width_of, title_run["lines"][0], title_run["size"], title_run["weight"])
    tag = step.get("tag")
    if tag:
        tw = text_width(width_of, tag, roles.get("tag", TAG_SIZE), 700) + 2 * TAG_PAD_X
        tag_at = step.get("tagAt")
        tx = x + w - tw - 12 if tag_at is None else x + w * tag_at - tw / 2
        placed["tagBox"] = {"x": tx, "y": y - TAG_H / 2, "w": tw, "h": TAG_H}
    return placed


def layout_swimlane_band(
    *,
    lanes: list[dict],
    steps: list[dict],
    cols: int,
    x: float,
    y: float,
    w: float,
    width_of: WidthOf,
    roles: dict,
    wrap_mode: WrapMode = "phrase",
    phases: list[dict] | None = None,
    boundaries: list[dict] | None = None,
    label_w: float | None = None,
    col_gap: float | None = None,
    fit: str | None = None,
) -> dict:
    """lib/swimlane.ts's layoutSwimlaneBand(). `steps` are already placed in columns (each
    carries `col`/`span`, as gantt()/table()'s rows already carry their own fields) — the
    DSL-level column assignment and boundary normalization (`swimlane()` in
    lib/dsl/sequence-table-swimlane.ts) is not ported."""
    pad_x, cw = x, w
    boundaries = boundaries or []
    chip_text = max([text_width(width_of, b["label"], roles["note"], 700) for b in boundaries if b.get("label")], default=0.0)
    min_label_w = math.ceil(chip_text) + 36 if chip_text else 0
    lw = label_w if label_w is not None else max(128, min_label_w)
    cg = col_gap if col_gap is not None else 28
    pad_x2 = 14.0
    pad_y = 14.0

    def col_w_at() -> float:
        return (cw - lw - 2 * pad_x2 - (cols - 1) * cg) / cols

    if fit == "shrink" and col_w_at() < SWIMLANE_COMFY_COL:
        for step_lw, step_cg, step_px in ((104, 20, 12), (88, 12, 8)):
            lw = min(lw, max(step_lw, min_label_w))
            cg = min(cg, step_cg)
            pad_x2 = min(pad_x2, step_px)
            if col_w_at() >= SWIMLANE_COMFY_COL:
                break
    if min_label_w > lw:
        raise ValueError(f"swimlane(): boundaries: the longest line name is {math.ceil(chip_text)}px wide and needs a label column of {min_label_w}px, but labelW is {lw}px — shorten the name or widen labelW")
    body_x = pad_x + lw
    col_w = col_w_at()
    if col_w < 60:
        hint = f"shorten the line names (they need a {min_label_w}px label column)" if min_label_w and lw <= min_label_w else "shrink labelW"
        raise ValueError(f"swimlane(): {cols} columns leave only {js_round(col_w)}px each — widen the diagram, {hint}, or use fewer columns")
    top0 = y
    start_y = snap_grid(top0)

    phase_h = 0.0
    laid_phases: list[dict] = []
    for ph in phases or []:
        px = body_x + pad_x2 + (ph["from"] - 1) * (col_w + cg) - cg / 2
        pw = (ph["to"] - ph["from"] + 1) * (col_w + cg)
        lines = _wrap_lines(ph["label"], roles["note"], 700, pw - 16, width_of, wrap_mode)
        phase_h = max(phase_h, len(lines) * roles["note"] * LINE_HEIGHT_EM + 16)
        laid_phases.append({"x": px, "w": pw, "lines": lines})

    steps_placed: list[dict] = []
    for st in steps:
        sx = body_x + pad_x2 + (st["col"] - 1) * (col_w + cg)
        sw = st["span"] * col_w + (st["span"] - 1) * cg
        steps_placed.append(_measure_box_like({**st, "padX": st.get("padX", 12), "padY": st.get("padY", 10)}, sx, 0, sw, width_of, roles, wrap_mode))

    lane_index = {lane["id"]: i for i, lane in enumerate(lanes)}
    row_gap = 12.0
    y2 = start_y + phase_h
    laid_lanes: list[dict] = []
    for i, lane in enumerate(lanes):
        label_lines = _wrap_lines(lane["label"], roles["title"], 700, lw - 24, width_of, wrap_mode)
        label_h = len(label_lines) * roles["title"] * LINE_HEIGHT_EM
        mine = [s for s in steps_placed if lane_index.get(s["lane"]) == i]
        max_step = max([s["h"] for s in mine], default=0.0)
        rows = 1 + max([s.get("row", 0) for s in mine], default=0)
        block_h = rows * max_step + (rows - 1) * row_gap
        chip_half = boundary_chip_h(roles["note"]) / 2 + 2
        n_chip = sum(1 for b in boundaries if b.get("label") and (b["after"] == lane["id"] or (lanes[i - 1]["id"] if i > 0 else None) == b["after"]))
        h = max(block_h, label_h + (2 * chip_half if n_chip else 0)) + 2 * pad_y
        laid_lanes.append({"y": y2, "h": h, "labelLines": label_lines, "labelTop": y2 + (h - label_h) / 2, **({"tone": lane["tone"]} if lane.get("tone") is not None else {}), "maxStep": max_step, "blockTop": y2 + (h - block_h) / 2})
        y2 += h

    laid_boundaries = []
    for b in boundaries:
        at = lane_index[b["after"]]
        nxt = laid_lanes[at + 1]
        laid_boundaries.append({"y": nxt["y"], **({"label": b["label"]} if b.get("label") else {})})

    frame: dict = {"type": "swimlane", "x": pad_x, "y": start_y, "w": cw, "h": y2 - start_y, "labelW": lw, "bodyX": body_x, "phaseH": phase_h, "phases": laid_phases, "lanes": laid_lanes}
    if laid_boundaries:
        frame["boundaries"] = laid_boundaries
    if fit == "shrink":
        narrow = _narrow_texts([r["lines"] for s in steps_placed for r in s["wrappedRuns"]])
        if narrow:
            frame["narrow"] = narrow

    for st in steps_placed:
        ln = laid_lanes[lane_index[st["lane"]]]
        st["y"] = snap_grid(ln["blockTop"] + st.get("row", 0) * (ln["maxStep"] + row_gap) + (ln["maxStep"] - st["h"]) / 2)
        if "tagBox" in st:
            st["tagBox"]["y"] = st["y"] - st["tagBox"]["h"] / 2

    return {"frame": frame, "steps": steps_placed}


def render_swimlane(b: dict, day: int | str = 1, roles: dict | None = None) -> str:
    """lib/emit-boxes.ts:280-313 renderSwimlane(): the frame (lanes/phases/boundaries).
    A swimlane's steps are plain boxes — render each with render_box() below."""
    from .emit_common import text_lines

    roles = roles or {"note": 14, "title": 15}
    parts: list[str] = []
    r = 8
    lanes = b["lanes"]
    n = len(lanes)
    has_ph = b["phaseH"] > 0
    x1 = b["x"] + b["w"]
    if has_ph:
        parts.append(f'<path d="{_rr_path(b["bodyX"], b["y"], x1 - b["bodyX"], b["phaseH"], tr=r)}" fill="{PALETTE[day]["soft"]}"/>')
        parts.append(f'<path d="{_rr_path(b["x"], b["y"], b["labelW"], b["phaseH"], tl=r)}" fill="{PALETTE["code"]}"/>')
        for ph in b["phases"]:
            parts.append(f'<path d="M{js_round(ph["x"])},{js_round(b["y"])} V{js_round(b["y"] + b["phaseH"])}" stroke="{PALETTE["border"]}" stroke-width="2"/>')
            parts.append(text_lines(ph["lines"], x=ph["x"] + ph["w"] / 2, top=b["y"] + 8, size=roles["note"], weight=700, anchor="middle", fill=PALETTE[day]["accent"]))
    for i, ln in enumerate(lanes):
        first = i == 0 and not has_ph
        last = i == n - 1
        body_fill = PALETTE["bg"] if i % 2 == 0 else PALETTE["code"]
        label_fill = PALETTE[day]["soft"] if ln.get("tone") == "accent" else PALETTE["code"]
        parts.append(f'<path d="{_rr_path(b["x"], ln["y"], b["labelW"], ln["h"], tl=(r if first else 0), bl=(r if last else 0))}" fill="{label_fill}"/>')
        parts.append(f'<path d="{_rr_path(b["bodyX"], ln["y"], x1 - b["bodyX"], ln["h"], tr=(r if first else 0), br=(r if last else 0))}" fill="{body_fill}"/>')
        if i > 0 or has_ph:
            parts.append(f'<path d="M{js_round(b["x"])},{js_round(ln["y"])} H{js_round(x1)}" stroke="{PALETTE["border"]}" stroke-width="2"/>')
        label_fill_text = PALETTE[day]["accent"] if ln.get("tone") == "accent" else PALETTE["text"]
        parts.append(text_lines(ln["labelLines"], x=b["x"] + b["labelW"] / 2, top=ln["labelTop"], size=roles["title"], weight=700, anchor="middle", fill=label_fill_text))
    parts.append(f'<path d="M{js_round(b["bodyX"])},{js_round(b["y"])} V{js_round(b["y"] + b["h"])}" stroke="{PALETTE["text"]}" stroke-width="2"/>')
    for bd in b.get("boundaries") or []:
        yy = js_round(bd["y"])
        parts.append(f'<path d="M{js_round(b["x"])},{yy} H{js_round(x1)}" stroke="{PALETTE["text"]}" stroke-width="3" stroke-dasharray="10,6"/>')
        if bd.get("label"):
            hh = boundary_chip_h(roles["note"])
            ww = b["labelW"] - 16
            parts.append(f'<rect x="{js_round(b["x"] + 8)}" y="{js_round(bd["y"] - hh / 2)}" width="{js_num(ww)}" height="{js_num(hh)}" rx="{js_num(hh / 2)}" fill="{PALETTE["bg"]}" stroke="{PALETTE["text"]}" stroke-width="1.5"/>')
            parts.append(text_lines([bd["label"]], x=b["x"] + b["labelW"] / 2, top=bd["y"] - hh / 2 + 3, size=roles["note"], weight=700, anchor="middle", fill=PALETTE["text"]))
    parts.append(f'<path d="{_rr_path(b["x"], b["y"], b["w"], b["h"], tl=r, tr=r, bl=r, br=r)}" fill="none" stroke="{PALETTE["text"]}" stroke-width="2.5"/>')
    return "\n  ".join(parts)


def render_box(step: dict, day: int | str = 1, roles: dict | None = None) -> str:
    """lib/emit-boxes.ts:89-95 renderBox(): a swimlane step is a plain box()."""
    roles = roles or {"note": 14}
    badge = ""
    if step.get("step") is not None:
        title_run = step["wrappedRuns"][0]
        title_baseline_y = step["y"] + step.get("padY", BOX_PAD_Y) + title_run["lineYs"][0]
        badge = "\n  " + render_step_badge(x=step["x"], pad_x=step.get("padX", BOX_PAD_X), title_baseline_y=title_baseline_y, step=step["step"], tone=step.get("tone"), dim=step.get("dim", False), day=day)
    tag = ""
    if step.get("tagBox"):
        tag = "\n  " + render_tag(tag_box=step["tagBox"], tag=step["tag"], tag_tone=step.get("tagTone"), tone=step.get("tone"), dim=step.get("dim", False), day=day, size=roles.get("tag", TAG_SIZE))
    frame = "" if step.get("frame") is False else render_box_rect(x=step["x"], y=step["y"], w=step["w"], h=step["h"], day=day, tone=step.get("tone"), dashed=step.get("dashed"), dim=step.get("dim", False)) + "\n  "
    text = _render_text_runs(step["wrappedRuns"], origin_x=step["x"] + step.get("padX", BOX_PAD_X), origin_y=step["y"] + step.get("padY", BOX_PAD_Y), w=step["w"] - 2 * step.get("padX", BOX_PAD_X), align=step.get("align", "left"), day=day, dim=step.get("dim", False), box_tone=step.get("tone"))
    stamp = render_stamp(x=step["x"], y=step["y"], w=step["w"], h=step["h"], stamp=step.get("stamp"), stamp_w=step.get("stampW"), note_size=roles["note"])
    return f"{frame}{text}{badge}{tag}{stamp}"


def _render_text_runs(wrapped_runs: list[dict], *, origin_x: float, origin_y: float, w: float, align: str, day: int | str, dim: bool, box_tone: str | None) -> str:
    """lib/emit-common.ts:68-91 renderTextRuns(), without spans (not ported for swimlane steps)."""
    parts: list[str] = []
    for run in wrapped_runs:
        color = PALETTE["muted"] if dim else run_color_of(run.get("tone"), box_tone, day)
        anchor = ' text-anchor="middle"' if align == "center" else ' text-anchor="end"' if align == "right" else ""
        indent = run.get("indent", 0)
        run_origin_x = origin_x + indent
        run_w = w - indent
        lx = run_origin_x + run_w / 2 if align == "center" else run_origin_x + run_w if align == "right" else run_origin_x
        for i, line in enumerate(run["lines"]):
            yy = origin_y + run["lineYs"][i]
            parts.append(f'<text x="{js_num(lx)}" y="{js_num(yy)}"{anchor} font-size="{run["size"]}" font-weight="{run["weight"]}" fill="{color}">{emoji_span(line)}</text>')
    return "\n  ".join(parts)


def _rr_path(x: float, y: float, w: float, h: float, *, tl: float = 0, tr: float = 0, br: float = 0, bl: float = 0) -> str:
    """lib/emit-common.ts:196-199 rrPath(): the `d` of a rectangle whose four corners are
    independently rounded (the caller wraps it in `<path d="...">`)."""
    x_, y_, w_, h_ = js_round(x), js_round(y), js_round(w), js_round(h)
    return (
        f"M{x_ + tl},{y_} H{x_ + w_ - tr} {f'A{tr},{tr} 0 0 1 {x_ + w_},{y_ + tr}' if tr else ''} "
        f"V{y_ + h_ - br} {f'A{br},{br} 0 0 1 {x_ + w_ - br},{y_ + h_}' if br else ''} "
        f"H{x_ + bl} {f'A{bl},{bl} 0 0 1 {x_},{y_ + h_ - bl}' if bl else ''} "
        f"V{y_ + tl} {f'A{tl},{tl} 0 0 1 {x_ + tl},{y_}' if tl else ''} Z"
    )
