"""1:1 port of lib/emit-boxes.ts — only renderBoxRect and a straight-line,
non-strong, non-double, unlabeled renderConnect (see the plan's scope
boundaries: elbow/loop routing, bend/weight/double-line and connector labels
are NOT ported — calling render_connect with any of those raises
NotImplementedError rather than silently drawing something wrong).

Golden master: lib/emit-boxes.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from typing import Callable

from .badge import badge_svg, pill_svg
from .emit_common import arrow_markers, emoji_span, escape_attr, escape_xml, js_num, js_round, line_attrs, snap4, text_lines
from .layout_util import STEP_BADGE_BASELINE_OFFSET, STEP_BADGE_R
from .tokens import CONNECT_LABEL_SIZE, PALETTE, TAG_SIZE, color_of, is_solid_tone, resolve_box_style, run_color_of, text_color_of, tone_style


def render_box_rect(
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    day: int | str = 1,
    tone: str | None = None,
    dashed: bool | None = None,
    dim: bool = False,
    data_node: str | None = None,
    default_tone: str = "plain",
    fill: str | None = None,
    stroke: str | None = None,
) -> str:
    """lib/emit-boxes.ts:56-63 renderBoxRect(). `fill`/`stroke` are a Python-only extension (not in
    Node): when given, they bypass tone resolution entirely and are used as literal colors — this
    path is NOT golden-tested (there is nothing in Node to compare it against); the tone-driven
    default path (fill=stroke=None) is the one the golden tests cover."""
    style = resolve_box_style(tone if tone is not None else default_tone, day, dashed)
    is_dashed = style["dashed"]
    fill = fill if fill is not None else style["fill"]
    stroke = stroke if stroke is not None else style["stroke"]
    if dim:
        fill = PALETTE["bg"]
        stroke = PALETTE["muted"]
    if is_dashed:
        dash = ' stroke-dasharray="6,4"'
    elif dim:
        dash = ' stroke-dasharray="2,5" stroke-linecap="round"'
    else:
        dash = ""
    # the right edge snaps like the left one (not the width alone) — lib/emit-boxes.ts:60-61
    rx = snap4(x)
    ry = snap4(y)
    rw = snap4(x + w) - rx
    rh = snap4(h)
    data_attr = f' data-node="{escape_attr(data_node)}"' if data_node else ""
    return f'<rect x="{js_num(rx)}" y="{js_num(ry)}" width="{js_num(rw)}" height="{js_num(rh)}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2.5"{dash}{data_attr}/>'


def render_connect_path(points: list[dict]) -> str:
    """lib/emit-boxes.ts:167-170 renderConnectPath(), straight (non-strong) case only."""
    parts = []
    for i, p in enumerate(points):
        prefix = "M" if i == 0 else "L"
        parts.append(f"{prefix}{js_num(js_round(p['x']))},{js_num(js_round(p['y']))}")
    return " ".join(parts)


def _point_at(points: list[dict], t: float) -> tuple[float, float]:
    """Position at fraction `t` along a polyline — a NEW, simplified stand-in for Node's
    layout-computed labelX/labelY (lib/layout.ts's resolveConnect(), not ported: that's
    layout-engine code). Fine for a 2-point straight line; a reasonable approximation for
    a longer polyline."""
    seg_lens = [((points[i + 1]["x"] - points[i]["x"]) ** 2 + (points[i + 1]["y"] - points[i]["y"]) ** 2) ** 0.5 for i in range(len(points) - 1)]
    total = sum(seg_lens) or 1.0
    target = total * t
    acc = 0.0
    for i, seg in enumerate(seg_lens):
        if acc + seg >= target or i == len(seg_lens) - 1:
            frac = 0 if seg == 0 else (target - acc) / seg
            a, b = points[i], points[i + 1]
            return a["x"] + (b["x"] - a["x"]) * frac, a["y"] + (b["y"] - a["y"]) * frac
        acc += seg
    return points[-1]["x"], points[-1]["y"]


def render_connect(
    *,
    points: list[dict],
    arrow: str | None = "end",
    weight: str | None = None,
    line: str | None = None,
    tone: str | None = None,
    dim: bool = False,
    label: str | None = None,
    chip: bool = False,
    label_at: float = 0.5,
    day: int | str = 1,
) -> str:
    """lib/emit-boxes.ts:173-196 renderConnect(), restricted to the branch the MVP ports: a plain
    straight/polyline with a marker arrowhead. Raises NotImplementedError for weight='strong' or
    line='double' — those need the AND-arc/strong-marker machinery that is out of scope.

    The line/arrowhead/chip DRAWING is byte-identical in style to Node (reuses render_connect_path,
    arrow_markers, pill_svg), but the label's POSITION (label_at fraction along the polyline) is a
    new, simplified stand-in for Node's layout-computed labelX/labelY — see _point_at()."""
    if weight == "strong":
        raise NotImplementedError("connect(weight='strong') is out of MVP scope")
    if line == "double":
        raise NotImplementedError("connect(line='double') is out of MVP scope")
    color = PALETTE["muted"] if dim else text_color_of(tone, day)
    d = render_connect_path(points)
    markers = arrow_markers(arrow, dim, False)
    path = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{line_attrs(line)}{markers}/>'
    if not label:
        return path
    label_x, label_y = _point_at(points, label_at)
    size = CONNECT_LABEL_SIZE
    if chip:
        from .approx_width import approx_width_of

        text_w = sum(approx_width_of(ch, size, 400) for ch in label)
        pad_x = 8
        bw, bh = text_w + 2 * pad_x, 24
        bx, by = label_x - bw / 2, label_y - bh / 2
        chip_svg = pill_svg(
            x=snap4(bx), y=snap4(by), w=snap4(bw), h=bh, fill=PALETTE["bg"], stroke=color,
            cx=label_x, baseline=label_y + 5, raw_y=by, text=color, size=size, weight=400, label_html=escape_xml(label),
        )
        return f"{path}\n  {chip_svg}"
    return f'{path}\n  <text x="{js_num(label_x)}" y="{js_num(label_y)}" text-anchor="middle" font-size="{size}" fill="{color}">{escape_xml(label)}</text>'


def render_stamp(*, x: float, y: float, w: float, h: float, stamp: str | None, stamp_w: float | None, note_size: float) -> str:
    """lib/emit-boxes.ts:82-86 renderStamp()."""
    if not stamp or stamp_w is None:
        return ""
    sx = snap4(x + w - 8 - stamp_w)
    sy = snap4(y + h - 6 - 24)
    return (
        f'\n  <rect x="{js_num(sx)}" y="{js_num(sy)}" width="{js_num(snap4(stamp_w))}" height="24" rx="4" fill="{PALETTE["bg"]}" stroke="{PALETTE["border"]}" stroke-width="1"/>\n'
        f'  <text x="{js_num(snap4(x + w - 8 - stamp_w / 2))}" y="{js_num(sy + 17)}" font-size="{note_size}" text-anchor="middle" fill="{PALETTE["muted"]}">{emoji_span(stamp)}</text>'
    )


def ringed(tone: str | None, dim: bool = False) -> bool:
    """lib/emit-boxes.ts:22 ringed(): a solid-tone box/badge gets a white ring to separate it from the fill."""
    return not dim and is_solid_tone(tone)


def render_tag(*, tag_box: dict, tag: str, tag_tone: str | None = None, tone: str | None = None, dim: bool = False, day: int | str = 1, size: float = TAG_SIZE) -> str:
    """lib/emit-boxes.ts:74-78 renderTag()."""
    fill = PALETTE["muted"] if dim else color_of(tone_style(tag_tone if tag_tone in ("danger", "muted") else "accent").ink, day)
    t = tag_box
    return pill_svg(
        x=snap4(t["x"]), y=snap4(t["y"]), w=snap4(t["w"]), h=t["h"], fill=fill,
        cx=t["x"] + t["w"] / 2, baseline=t["y"] + 17, raw_y=t["y"], text=PALETTE["bg"],
        stroke=PALETTE["bg"] if ringed(tone, dim) else None, size=size, label_html=emoji_span(tag),
    )


def render_step_badge(*, x: float, pad_x: float, title_baseline_y: float, step: int | str, tone: str | None = None, dim: bool = False, day: int | str = 1) -> str:
    """lib/emit-boxes.ts:25-36 renderStepBadge(), restricted to left-aligned titles with no icon
    offset (this port's model.py has no align/icon option yet — see the plan's deferred items)."""
    cx = x + pad_x + STEP_BADGE_R
    cy = title_baseline_y - STEP_BADGE_BASELINE_OFFSET
    return badge_svg(
        cx=cx, cy=cy, r=STEP_BADGE_R, w=2 * STEP_BADGE_R, shape="circle", label=str(step), aria=f"手順 {step}",
        size=16, fill=PALETTE[day]["accent"], stroke=PALETTE["bg"] if ringed(tone, dim) else None,
        baseline=title_baseline_y, snap=snap4, esc=escape_xml,
    )


def render_caption(*, x: float, y: float, w: float, text: str, size: float, align: str = "center", tone: str | None = None, day: int | str = 1, mono: bool = False) -> str:
    """lib/emit-boxes.ts:49-51 renderCaption(). Uses text_lines (the layout-independent
    primitive — see model.py) in place of the real renderTextRuns()/wrappedRuns pipeline."""
    anchor = {"left": "start", "center": "middle", "right": "end"}.get(align, align)
    tx = {"start": x, "middle": x + w / 2, "end": x + w}[anchor]
    return text_lines([text], x=tx, top=y - size, size=size, weight=700, anchor=anchor, fill=text_color_of(tone, day), mono=mono)


def render_group_rect(*, x: float, y: float, w: float, h: float, day: int | str = 1, tone: str | None = None, dashed: bool | None = None, dim: bool = False) -> str:
    """lib/emit-boxes.ts:98-101 renderGroup() (frame part only; the stamp and the title
    caption are composed separately in model.py, same split as Node's layout does)."""
    return render_box_rect(x=x, y=y, w=w, h=h, day=day, tone=tone or "muted", dashed=dashed, dim=dim, default_tone="muted")


def render_banner(*, x: float, y: float, w: float, h: float, lines: list[str], size: float, day: int | str = 1, tone: str | None = None, pad_x: float = 20, pad_y: float = 16) -> str:
    """lib/emit-boxes.ts:148-150 renderBanner(): an accent-filled box with centered text."""
    rect = render_box_rect(x=x, y=y, w=w, h=h, day=day, tone=tone or "accent", default_tone="accent")
    fill_color = run_color_of(None, tone or "accent", day)
    text = text_lines(lines, x=x + w / 2, top=y + pad_y, size=size, weight=700, anchor="middle", fill=fill_color) if lines else ""
    return f"{rect}\n  {text}" if text else rect


def render_raw(*, x: float, y: float, w: float, h: float, day: int | str, draw: Callable[[dict], str]) -> str:
    """lib/emit-boxes.ts:268-276 renderRaw(): hands the caller a rect + a tone->hex color lookup, and
    draws exactly what it returns — the escape hatch for a shape this port has no primitive for."""

    def color(tone: str) -> str:
        if tone == "accent":
            return PALETTE[day]["accent"]
        if tone == "accent-soft":
            return PALETTE[day]["soft"]
        return PALETTE.get(tone, PALETTE["text"])

    return draw({"x": x, "y": y, "w": w, "h": h, "day": day, "color": color})
