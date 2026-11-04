"""1:1 port of the <svg> wrapper assembled by lib/emit.ts's emitSvgWith().

emitSvgWith() itself is not exported by Node (only emitSvg(), which requires
a full LaidOutDiagram — impractical to construct for a golden test, see the
plan). So this wrapper was instead verified by calling the real, exported
emitSvg() directly with a minimal fake LaidOutDiagram and diffing the
captured output byte-for-byte against this function — see
golden/fixtures/svg_wrapper_empty.json and svg_wrapper_box_connect.json,
and tests/test_svg_wrapper.py which replays that capture.

Scope kept out of this port (see lib/emit.ts): dark mode (recolor()),
doc-medium a11y (<title>/<desc>/<metadata>), transparent backgrounds, tone
overrides, canvas/minText, dim/strong/double-line arrow marker variants.
"""

from __future__ import annotations

from .emit_common import js_num
from .tokens import FONT_STACKS, PALETTE


def emit_svg(*, width: float, height: float, body: str = "", connect_svg: str = "", has_arrow: bool = False) -> str:
    """lib/emit.ts:99-105, restricted to: light theme, medium != 'doc', transparent=False,
    no tone overrides, only the plain 'dsl-arrow' marker (no dim/strong/double variants)."""
    width_s, height_s = js_num(width), js_num(height)
    defs = ""
    if has_arrow:
        defs = (
            "\n  <defs>"
            '\n    <marker id="dsl-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'\n      <path d="M0,0 L10,5 L0,10 z" fill="{PALETTE["text"]}"/>'
            "\n    </marker>"
            "\n  </defs>"
        )
    style = f"\n    text {{ font-family: {FONT_STACKS['sans']}; }}" f"\n    .emoji {{ font-family: {FONT_STACKS['emoji']}; }}"
    bg_rect = f'\n  <rect x="0" y="0" width="{width_s}" height="{height_s}" fill="{PALETTE["bg"]}"/>'
    connect_part = f"\n\n  {connect_svg}" if connect_svg else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_s}" height="{height_s}" viewBox="0 0 {width_s} {height_s}">{defs}'
        "\n  <style>" + style + "\n  </style>" + bg_rect + "\n\n  " + body + connect_part + "\n</svg>\n"
    )
