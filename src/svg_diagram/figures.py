"""1:1 port of selected renderers from lib/emit-figures.ts: pyramid() and curve() — both
closed-form (no auto-layout/crossing-reduction engine needed, unlike cause()/bpmn()/tree()).

Golden master: lib/emit-figures.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .emit_common import emoji_span, js_num, js_round
from .tokens import PALETTE


def render_pyramid(layers: list[dict], day: int | str = 1, title_size: float = 15) -> str:
    """lib/emit-figures.ts:199-209 renderPyramid(). Each layer: {points: [[x,y]]*4, opacity,
    textColor, lines: [str], textYs: [float], cx}."""
    accent = PALETTE[day]["accent"]
    out = []
    for layer in layers:
        pts = " ".join(f"{js_round(px)},{js_round(py)}" for px, py in layer["points"])
        shape = f'<polygon points="{pts}" fill="{accent}" fill-opacity="{js_num(layer["opacity"])}" stroke="{accent}" stroke-width="2.5"/>'
        text = "\n  ".join(
            f'<text x="{js_round(layer["cx"])}" y="{js_num(layer["textYs"][i])}" text-anchor="middle" font-size="{title_size}" font-weight="700" fill="{layer["textColor"]}">{emoji_span(line)}</text>'
            for i, line in enumerate(layer["lines"])
        )
        out.append(f"{shape}\n  {text}")
    return "\n\n  ".join(out)


def pyramid_layer_geometry(*, n: int, i: int, base_width: float, apex_ratio: float, layer_height: float, cx: float, stack_bottom_y: float) -> dict:
    """lib/layout-handlers.ts:514-532 layoutPyramid()'s per-layer geometry (points, y-span,
    opacity) — pure closed-form arithmetic, no text metrics, so this IS byte-identical to
    Node (unlike the text-wrapping step, which uses this port's approximate width function).
    `i`=0 is the bottom (widest) layer; `stack_bottom_y` is the pyramid's own bottom edge y."""
    from .tokens import SHADES

    apex_width = base_width * apex_ratio
    bottom_y = stack_bottom_y - i * layer_height
    top_y = bottom_y - layer_height
    bottom_w = base_width - (base_width - apex_width) * (i / n)
    top_w = base_width - (base_width - apex_width) * ((i + 1) / n)
    opacity = SHADES[min(len(SHADES) - 1, n - 1 - i)]
    points = [
        (cx - bottom_w / 2, bottom_y), (cx + bottom_w / 2, bottom_y),
        (cx + top_w / 2, top_y), (cx - top_w / 2, top_y),
    ]
    return {"points": points, "bottomY": bottom_y, "topY": top_y, "bottomW": bottom_w, "topW": top_w, "opacity": opacity}


def render_curve(
    *,
    axis_x: float,
    axis_right: float,
    axis_top: float,
    axis_bottom: float,
    points: list[dict],
    day: int | str = 1,
    y_top_label: str | None = None,
    y_bottom_label: str | None = None,
    x_label: str | None = None,
) -> str:
    """lib/emit-figures.ts:235-255 renderCurve(). `points`: [{x, y, emphasis?, dropLine?}] in
    already-laid-out pixel coordinates (see curve_points() for the closed-form x/y mapping)."""
    from .tokens import color_of, tone_style

    parts = [
        f'<path d="M{js_round(axis_x)},{js_round(axis_top)} L{js_round(axis_x)},{js_round(axis_bottom)} L{js_round(axis_right)},{js_round(axis_bottom)}" fill="none" stroke="{PALETTE["text"]}" stroke-width="2"/>',
        '<path d="' + " ".join(f"{'M' if i == 0 else 'L'}{js_round(p['x'])},{js_round(p['y'])}" for i, p in enumerate(points)) + f'" fill="none" stroke="{PALETTE["text"]}" stroke-width="3"/>',
    ]

    def emph_color(emphasis: str) -> str:
        key = emphasis if emphasis in ("accent", "danger") else "muted"
        return color_of(tone_style(key).ink, day)

    for i, p in enumerate(points):
        color = emph_color(p["emphasis"]) if p.get("emphasis") else (PALETTE[day]["accent"] if i == 0 else PALETTE["muted"])
        r = 8 if p.get("emphasis") == "danger" else (6 if i == 0 else 5)
        if p.get("dropLine"):
            parts.append(f'<path d="M{js_round(p["x"])},{js_round(p["y"])} L{js_round(p["x"])},{js_round(axis_bottom)}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="6,4"/>')
        from .emit_common import snap4

        parts.append(f'<circle cx="{snap4(p["x"])}" cy="{snap4(p["y"])}" r="{r}" fill="{color}"/>')

    from .emit_common import escape_xml

    if y_top_label:
        parts.append(f'<text x="{js_round(axis_x - 8)}" y="{js_round(axis_top + 4)}" text-anchor="end" font-size="14" fill="{PALETTE["muted"]}">{escape_xml(y_top_label)}</text>')
    if y_bottom_label:
        parts.append(f'<text x="{js_round(axis_x - 8)}" y="{js_round(axis_bottom)}" text-anchor="end" font-size="14" fill="{PALETTE["muted"]}">{escape_xml(y_bottom_label)}</text>')
    if x_label:
        parts.append(f'<text x="{js_round(axis_x)}" y="{js_round(axis_bottom + 24)}" font-size="14" fill="{PALETTE["muted"]}">{escape_xml(x_label)}</text>')
    return "\n  ".join(parts)


def curve_points(*, raw_points: list[dict], axis_x: float, axis_right: float, axis_top: float, axis_bottom: float) -> list[dict]:
    """lib/layout-handlers.ts:567-573 layoutCurve()'s point placement — pure closed-form
    arithmetic (evenly spaced x, y interpolated 0..1 top..bottom), byte-identical to Node."""
    n = len(raw_points)
    out = []
    for i, p in enumerate(raw_points):
        x = axis_x if n == 1 else axis_x + i * (axis_right - axis_x) / (n - 1)
        y = axis_bottom - max(0, min(1, p["y"])) * (axis_bottom - axis_top)
        out.append({"x": x, "y": y, "emphasis": p.get("emphasis"), "dropLine": bool(p.get("dropLine"))})
    return out
