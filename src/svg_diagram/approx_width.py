"""A standard-library-only APPROXIMATION of text width, for production use by the layout
algorithms in this package (cloud()/mindmap()/tree()/cause(), row()/grid() flex sizing).

This does NOT match Node.js's real measurement (lib/measure.ts/lib/font-metrics.ts), which
shapes text with the actual HarfBuzz library against real font files for byte-accurate
widths. Matching that in Python would need `uharfbuzz` + bundled font files — an external
dependency this project deliberately avoids, because the whole point of the Python port is
to run inside AI code-execution sandboxes that often forbid installing extra libraries
(see the deep-research report on ChatGPT/Gemini/M365 Copilot earlier in this project).

So: layout DECISIONS (where line breaks fall, how big a box needs to be, how nodes are
positioned) are ported faithfully from Node's algorithms (same inputs -> same structural
outputs), but they run on approximate widths here, so the exact pixel values will differ
from Node's output. This is a deliberate, documented trade-off, not a bug.
"""

from __future__ import annotations

from .atoms import is_cjk

# Rough average glyph-width-to-em-size ratios for the FONT_STACKS.sans stack (Hiragino
# Sans/Yu Gothic/Meiryo/Noto Sans JP) at weight 400. Calibrated by eye against typical
# proportional sans metrics, not measured — see module docstring.
_CJK_EM = 1.0  # fullwidth characters are ~square
_DIGIT_EM = 0.55
_UPPER_EM = 0.62
_LOWER_EM = 0.50
_SPACE_EM = 0.28
_PUNCT_EM = 0.32
_DEFAULT_EM = 0.55
_MONO_EM = 0.6  # lib/tokens.ts FONT_STACKS.mono: fixed-width by design
_BOLD_FACTOR = 1.08  # bold glyphs render a little wider than regular


def _char_em(ch: str) -> float:
    if is_cjk(ch):
        return _CJK_EM
    if ch == " ":
        return _SPACE_EM
    if ch.isdigit():
        return _DIGIT_EM
    if ch.isupper():
        return _UPPER_EM
    if ch.islower():
        return _LOWER_EM
    if not ch.isalnum():
        return _PUNCT_EM
    return _DEFAULT_EM


def approx_width_of(atom: str, size: float, weight: float = 400, font: str = "sans") -> float:
    """Matches the `WidthOf` signature (lib/types/core.ts) so it can be injected wherever
    Node's layout code injects its real `widthOf`."""
    if font == "mono":
        per_char = _MONO_EM
        total = sum(per_char for _ in atom) * size
    else:
        total = sum(_char_em(ch) for ch in atom) * size
    if weight >= 700:
        total *= _BOLD_FACTOR
    return total
