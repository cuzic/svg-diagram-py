"""1:1 port of lib/badge.ts — badgeSvg()/pillSvg(), the shared primitives behind
box({step}) badges, tag pills, and connector labels.

Golden master: lib/badge.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
from typing import Callable, Literal

from .emit_common import js_num, js_round
from .tokens import PALETTE, wcag_ratio

BadgeShape = Literal["circle", "square", "triangle"]

BADGE_R = 11  # lib/badge.ts:18
INK_MID = 0.38  # lib/badge.ts:22
_BADGE_PAD = 6
_APEX = 3


def badge_box(cx: float, cy: float, text_w: float, r: float = BADGE_R, shape: BadgeShape = "circle") -> dict:
    """lib/badge.ts:26-30 badgeBox()."""
    reach = r + _APEX if shape == "triangle" else r
    w = max(2 * reach, text_w + 2 * _BADGE_PAD)
    return {
        "x": cx - w / 2,
        "y": cy - r - (_APEX if shape == "triangle" else 0),
        "w": w,
        "h": 2 * r + (_APEX if shape == "triangle" else 0),
    }


def badge_text_key(fill_hex: str) -> Literal["bg", "text"]:
    """lib/badge.ts:33-35 badgeTextKey()."""
    return "bg" if wcag_ratio(PALETTE["bg"], fill_hex) >= wcag_ratio(PALETTE["text"], fill_hex) else "text"


def badge_svg(
    *,
    cx: float,
    cy: float,
    shape: BadgeShape,
    r: float,
    w: float,
    label: str,
    aria: str,
    size: float,
    weight: float = 700,
    fill: str,
    stroke: str | None = None,
    sw: float = 2,
    text: str | None = None,
    baseline: float | None = None,
    snap: Callable[[float], float],
    esc: Callable[[str], str],
) -> str:
    """lib/badge.ts:47-72 badgeSvg()."""
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    if shape == "triangle":
        hw = w / 2
        cx_r = js_round(cx)
        top = js_round(cy) - r - _APEX
        bottom = js_round(cy) + r

        def p(x: float, y: float) -> str:
            return f"{js_round(x)},{js_round(y)}"

        side = math.hypot(hw, bottom - top)
        inradius = (w * (bottom - top) / 2) / ((w + 2 * side) / 2)
        cy_r = bottom - inradius
        shape_svg = f'<path d="M{p(cx_r, top)} L{p(cx_r + hw, bottom)} L{p(cx_r - hw, bottom)} Z" fill="{fill}"{st} stroke-linejoin="round"/>'
    elif shape == "square" or w > 2 * r:
        x0, x1, y0, y1 = snap(cx - w / 2), snap(cx + w / 2), snap(cy - r), snap(cy + r)
        cx_r, cy_r = (x0 + x1) / 2, (y0 + y1) / 2
        rx = 3 if shape == "square" else r
        shape_svg = f'<rect x="{js_num(x0)}" y="{js_num(y0)}" width="{js_num(x1 - x0)}" height="{js_num(y1 - y0)}" rx="{js_num(rx)}" fill="{fill}"{st}/>'
    else:
        cx_r, cy_r = snap(cx), snap(cy)
        shape_svg = f'<circle cx="{js_num(cx_r)}" cy="{js_num(cy_r)}" r="{js_num(r)}" fill="{fill}"{st}/>'

    base = baseline if baseline is not None else cy_r + size * INK_MID
    text_fill = text if text is not None else PALETTE[badge_text_key(fill)]
    text_svg = "" if label == "" else f'\n  <text x="{js_num(cx_r)}" y="{js_round(base)}" text-anchor="middle" font-size="{js_num(size)}" font-weight="{js_num(weight)}" fill="{text_fill}">{esc(label)}</text>'
    return f'<g role="img" aria-label="{esc(aria).replace(chr(34), "&quot;")}" data-badge="">\n  {shape_svg}{text_svg}\n  </g>'


def pill_svg(
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str,
    stroke: str | None = None,
    sw: float = 2,
    dash: str | None = None,
    cx: float,
    baseline: float,
    text: str,
    size: float,
    weight: float = 700,
    label_html: str,
    raw_y: float | None = None,
) -> str:
    """lib/badge.ts:89-92 pillSvg()."""
    dash_attr = f' stroke-dasharray="{dash}"' if (stroke and dash) else ""
    st = f' stroke="{stroke}" stroke-width="{sw}"{dash_attr}' if stroke else ""
    y_offset = 0 if raw_y is None else y - raw_y
    weight_attr = "" if weight == 400 else f' font-weight="{js_num(weight)}"'
    return (
        f'<rect x="{js_num(x)}" y="{js_num(y)}" width="{js_num(w)}" height="{js_num(h)}" rx="{js_num(h / 2)}" fill="{fill}"{st}/>\n'
        f'  <text x="{js_round(cx)}" y="{js_round(baseline + y_offset)}" text-anchor="middle" font-size="{js_num(size)}"{weight_attr} fill="{text}">{label_html}</text>'
    )
