"""1:1 port of lib/emit-common.ts — only the pieces the MVP drawing layer needs.

Golden master: lib/emit-common.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
import re

# lib/tokens.ts:332 EMOJI_RE (the 'u' flag is implicit: Python str is already full Unicode)
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF⭐⚠❤]")

LH_EM = 1.4  # lib/emit-common.ts:173
ARROW_L = 12  # lib/cause-hop.ts:11


def js_round(n: float) -> int:
    """Matches JS ``Math.round``: ties round toward +Infinity (Python's round() uses banker's rounding, which differs)."""
    return math.floor(n + 0.5)


def js_num(n: float) -> str:
    """Matches how a JS template literal stringifies a number (``${n}``): no trailing ``.0`` for integer-valued floats."""
    if isinstance(n, int):
        return str(n)
    if n == int(n):
        return str(int(n))
    return repr(n)


def snap4(n: float) -> int:
    """lib/emit-common.ts:10-12 snap4()."""
    return js_round(n / 4) * 4


def round1(n: float) -> float:
    """The ``const r1 = (v: number) => Math.round(v * 10) / 10;`` one-tenth rounding helper
    every chart module (lib/charts-*.ts) redefines locally — hoisted here once since it has
    no module-specific state."""
    return js_round(n * 10) / 10


_XML_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
_XML_ESC_RE = re.compile(r"[&<>]")


def escape_xml(s: str) -> str:
    """lib/emit-common.ts:15-19 escapeXml()."""
    return _XML_ESC_RE.sub(lambda m: _XML_ESC[m.group(0)], s)


def escape_attr(s: str) -> str:
    """lib/emit-common.ts:22 escapeAttr()."""
    return escape_xml(s).replace('"', "&quot;")


def emoji_span(text: str) -> str:
    """lib/emit-common.ts:27-37 emojiSpan(). Equals escape_xml(text) when text has no emoji codepoints."""
    out: list[str] = []
    last = 0
    for m in EMOJI_RE.finditer(text):
        out.append(escape_xml(text[last : m.start()]))
        out.append(f'<tspan class="emoji">{escape_xml(m.group(0))}</tspan>')
        last = m.end()
    out.append(escape_xml(text[last:]))
    return "".join(out)


def line_attrs(line: str | None) -> str:
    """lib/emit-common.ts:94-96 lineAttrs(). 'double' and strong-weight styling are out of MVP scope."""
    if line == "dashed":
        return ' stroke-dasharray="6,4"'
    if line == "dotted":
        return ' stroke-dasharray="2,5" stroke-linecap="round"'
    return ""


def arrow_markers(arrow: str | None, dim: bool = False, strong: bool = False) -> str:
    """lib/emit-common.ts:99-102 arrowMarkers()."""
    marker_id = f"dsl-arrow{'-strong' if strong else ''}{'-dim' if dim else ''}"
    start = f' marker-start="url(#{marker_id})"' if arrow in ("start", "both") else ""
    end = f' marker-end="url(#{marker_id})"' if arrow in ("end", "both") else ""
    return start + end


def _sign(n: float) -> int:
    """Matches JS Math.sign for the finite, non-zero inputs arrow_path() uses."""
    return (n > 0) - (n < 0)


def _cut_path(pts: list[dict], cuts: list[dict]) -> str:
    """lib/emit-common.ts:131-143 cutPath(): a hop (a bump of height `r` toward `side`) over
    another line, at each point of `cuts` that lies on one of `pts`'s runs (ADR 0028)."""

    def f(n: float) -> str:
        return str(snap4(n))

    first = pts[0]
    d = f"M{f(first['x'])},{f(first['y'])}"
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        length = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
        ux, uy = (b["x"] - a["x"]) / length, (b["y"] - a["y"]) / length
        here = sorted(
            (c for c in cuts if abs((c["x"] - a["x"]) * uy - (c["y"] - a["y"]) * ux) < 0.5 and 0 < (c["x"] - a["x"]) * ux + (c["y"] - a["y"]) * uy < length),
            key=lambda c: (c["x"] - a["x"]) * ux + (c["y"] - a["y"]) * uy,
        )
        for c in here:
            d += f" L{f(c['x'] - ux * c['r'])},{f(c['y'] - uy * c['r'])} Q{f(c['x'] + c['side']['x'] * 2 * c['r'])},{f(c['y'] + c['side']['y'] * 2 * c['r'])} {f(c['x'] + ux * c['r'])},{f(c['y'] + uy * c['r'])}"
        d += f" L{f(b['x'])},{f(b['y'])}"
    return d


def arrow_path(
    points: list[dict],
    color: str,
    line: str | None,
    width: float = 2,
    head_at: str = "end",
    end: str = "arrow",
    cuts: list | None = None,
) -> str:
    """lib/emit-common.ts:149-169 arrowPath(): a filled-triangle arrowhead baked into the path
    (not a <marker>), used where a marker on a reversed end would not be trusted by every
    renderer (legend AND/back/blocks lines, cloud()'s double-headed conflict arrow). `cuts`
    (hop-over bumps over a crossing line, ADR 0028): cause()'s engine, used only on the
    non-`end='bar'` path (a cutting arrow never gets cuts — causeCrossings() never marks a
    `kind: 'blocks'` edge as the "over" of a crossing)."""
    pts = [dict(p) for p in points]
    heads: list[str] = []

    def head(tip: dict, frm: dict) -> dict:
        dx, dy = _sign(tip["x"] - frm["x"]), _sign(tip["y"] - frm["y"])
        tx, ty = snap4(tip["x"]), snap4(tip["y"])
        w = 5
        heads.append(
            f'<path d="M{js_num(tx)},{js_num(ty)} L{js_num(tx - dx * ARROW_L - dy * w)},{js_num(ty - dy * ARROW_L + dx * w)} '
            f'L{js_num(tx - dx * ARROW_L + dy * w)},{js_num(ty - dy * ARROW_L - dx * w)} z" fill="{color}"/>'
        )
        return {"x": tip["x"] - dx * (ARROW_L - 2), "y": tip["y"] - dy * (ARROW_L - 2)}

    n = len(pts)
    effective_line = None if line == "solid" else line
    if end == "bar":
        tip, frm = points[n - 1], points[n - 2]
        dx, dy = _sign(tip["x"] - frm["x"]), _sign(tip["y"] - frm["y"])
        w, off = 10, 3
        bx, by = snap4(tip["x"] - dx * off), snap4(tip["y"] - dy * off)
        pts[n - 1] = {"x": tip["x"] - dx * off, "y": tip["y"] - dy * off}
        heads.append(f'<path d="M{js_num(bx - dy * w)},{js_num(by + dx * w)} L{js_num(bx + dy * w)},{js_num(by - dx * w)}" fill="none" stroke="{color}" stroke-width="3"/>')
        d = "M" + " L".join(f"{js_num(snap4(p['x']))},{js_num(snap4(p['y']))}" for p in pts)
        path = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{js_num(width)}"{line_attrs(effective_line)}/>'
        return f"{path}\n  " + "\n  ".join(heads)
    pts[n - 1] = head(points[n - 1], points[n - 2])
    if head_at == "both":
        pts[0] = head(points[0], points[1])
    if cuts:
        d = _cut_path(pts, cuts)
    else:
        d = "M" + " L".join(f"{js_num(snap4(p['x']))},{js_num(snap4(p['y']))}" for p in pts)
    path = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{js_num(width)}"{line_attrs(effective_line)}/>'
    return f"{path}\n  " + "\n  ".join(heads)


def stroke_line(d: str, color: str, line: str | None, arrow: str | None, width: float = 2) -> str:
    """lib/emit-common.ts:176-181 strokeLine()."""
    from .tokens import PALETTE

    if line == "double":
        return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="6"/>\n  <path d="{d}" fill="none" stroke="{PALETTE["bg"]}" stroke-width="2"{arrow_markers(arrow)}/>'
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{js_num(width)}"{line_attrs(line)}{arrow_markers(arrow)}/>'


def text_lines(
    lines: list[str],
    *,
    x: float,
    top: float,
    size: int,
    weight: int = 400,
    anchor: str = "start",
    fill: str,
    mono: bool = False,
) -> str:
    """lib/emit-common.ts:184-192 textLines(). A layout-independent single-run text helper (no auto-wrap, no measurement)."""
    a = ' text-anchor="middle"' if anchor == "middle" else ' text-anchor="end"' if anchor == "end" else ""
    cls = ' class="mono"' if mono else ""
    parts = []
    for k, line in enumerate(lines):
        y = js_round(top + size + k * size * LH_EM)
        parts.append(f'<text x="{js_round(x)}" y="{y}"{a}{cls} font-size="{size}" font-weight="{weight}" fill="{fill}">{emoji_span(line)}</text>')
    return "\n  ".join(parts)
