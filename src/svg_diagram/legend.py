"""1:1 port of the common branches of lib/emit-boxes.ts's renderLegend(): tone swatches
(incl. the double-frame variant), plain connector lines, and the AND/back/blocks edge
symbols. NOT ported (deferred, niche/project-specific): FTA event/gate swatches
(ftaLegendSwatch, lib/emit-fta.ts), the hex-color swatch polygon, and strong/double-line
swatches (same "out of MVP scope" boundary as render_connect).

Golden master: lib/emit-boxes.ts:105-145 renderLegend() (Node.js, svg-diagram).
"""

from __future__ import annotations

from .emit_common import arrow_markers, arrow_path, emoji_span, js_num, js_round, line_attrs, snap4
from .tokens import PALETTE, resolve_box_style
from .layout_util import LEGEND_SWATCH_W


def render_legend_item(*, x: float, y: float, label: str, kind: str = "swatch", day: int | str = 1, note_size: float = 14, **opts) -> str:
    """One legend row. `kind`: 'swatch' (opts: tone?, dashed?, mark?: bool, double?: bool),
    'line' (opts: line?, arrow?), 'and', 'back', 'blocks'."""
    cy = y + 12
    parts: list[str] = []

    if kind == "swatch":
        style = resolve_box_style(opts.get("tone"), day, opts.get("dashed"))
        sx, sy = x + 4, cy - 8
        dash = ' stroke-dasharray="6,4"' if style["dashed"] else ""
        sw = 3.5 if opts.get("mark") else 2.5
        parts.append(f'<rect x="{snap4(sx)}" y="{snap4(sy)}" width="28" height="16" rx="4" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="{sw}"{dash}/>')
        if opts.get("double"):
            parts.append(f'<rect x="{snap4(sx + 3)}" y="{snap4(sy + 3)}" width="22" height="10" rx="2" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="1.5"/>')
    elif kind == "line":
        if opts.get("weight") == "strong" or opts.get("line") == "double":
            raise NotImplementedError("legend(line: strong/double) is out of MVP scope")
        d = f"M{snap4(x)},{js_num(cy)} L{snap4(x + LEGEND_SWATCH_W)},{js_num(cy)}"
        parts.append(f'<path d="{d}" fill="none" stroke="{PALETTE["text"]}" stroke-width="2"{line_attrs(opts.get("line"))}{arrow_markers(opts.get("arrow", "end"))}/>')
    elif kind == "and":
        for dy in (-5, 5):
            parts.append(arrow_path([{"x": x, "y": cy + dy}, {"x": x + LEGEND_SWATCH_W, "y": cy + dy}], PALETTE["text"], None))
        parts.append(f'<path d="M{snap4(x + 14)},{js_num(cy - 5)} Q{snap4(x + 20)},{js_num(cy)} {snap4(x + 14)},{js_num(cy + 5)}" fill="none" stroke="{PALETTE["text"]}" stroke-width="2"/>')
    elif kind == "back":
        parts.append(arrow_path([{"x": x, "y": cy}, {"x": x + LEGEND_SWATCH_W, "y": cy}], PALETTE["text"], None, 3))
    elif kind == "blocks":
        parts.append(arrow_path([{"x": x, "y": cy}, {"x": x + LEGEND_SWATCH_W, "y": cy}], PALETTE["text"], "dashed", 2, "end", "bar"))
    else:
        raise ValueError(f"legend: unknown kind {kind!r}")

    parts.append(f'<text x="{js_round(x + LEGEND_SWATCH_W + 8)}" y="{js_num(cy + 5)}" font-size="{note_size}" fill="{PALETTE["text"]}">{emoji_span(label)}</text>')
    return "\n  ".join(parts)


def render_legend(items: list[dict], day: int | str = 1, note_size: float = 14) -> str:
    """lib/emit-boxes.ts:105-145 renderLegend()."""
    return "\n  ".join(render_legend_item(day=day, note_size=note_size, **item) for item in items)
