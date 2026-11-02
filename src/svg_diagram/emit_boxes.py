"""1:1 port of lib/emit-boxes.ts — only renderBoxRect and a straight-line,
non-strong, non-double, unlabeled renderConnect (see the plan's scope
boundaries: elbow/loop routing, bend/weight/double-line and connector labels
are NOT ported — calling render_connect with any of those raises
NotImplementedError rather than silently drawing something wrong).

Golden master: lib/emit-boxes.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .emit_common import arrow_markers, escape_attr, js_num, js_round, line_attrs, snap4
from .tokens import PALETTE, resolve_box_style, text_color_of


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


def render_connect(
    *,
    points: list[dict],
    arrow: str | None = "end",
    weight: str | None = None,
    line: str | None = None,
    tone: str | None = None,
    dim: bool = False,
    label: str | None = None,
    day: int | str = 1,
) -> str:
    """lib/emit-boxes.ts:173-196 renderConnect(), restricted to the branch the MVP ports: a plain
    straight line with a marker arrowhead. Raises NotImplementedError for weight='strong',
    line='double' or a label — those need pillSvg()/badge.ts machinery that is out of scope."""
    if weight == "strong":
        raise NotImplementedError("connect(weight='strong') is out of MVP scope")
    if line == "double":
        raise NotImplementedError("connect(line='double') is out of MVP scope")
    if label:
        raise NotImplementedError("connect(label=...) is out of MVP scope (needs badge.ts's pillSvg)")
    color = PALETTE["muted"] if dim else text_color_of(tone, day)
    d = render_connect_path(points)
    markers = arrow_markers(arrow, dim, False)
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{line_attrs(line)}{markers}/>'
