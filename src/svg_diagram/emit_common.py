"""1:1 port of lib/emit-common.ts — only the pieces the MVP drawing layer needs.

Golden master: lib/emit-common.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
import re

# lib/tokens.ts:332 EMOJI_RE (the 'u' flag is implicit: Python str is already full Unicode)
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF⭐⚠❤]")

LH_EM = 1.4  # lib/emit-common.ts:173


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
