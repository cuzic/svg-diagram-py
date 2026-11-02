"""1:1 port of lib/atoms.ts — splitting text into "break atoms" and summing their
widths. Pure algorithm; the actual per-atom width comes from an injected
`width_of` callback (see Phase A notes in the plan) — this file knows nothing
about fonts.

Golden master: lib/atoms.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import re
from typing import Callable

FontFamily = str  # 'sans' | 'mono' | 'emoji' — kept as plain str, like the TS union erased at runtime
WidthOf = Callable[[str, float, float, FontFamily], float]

_WHITESPACE_RE = re.compile(r"\s")


def is_cjk(ch: str) -> bool:
    """lib/atoms.ts:5-11 isCJK()."""
    c = ord(ch)
    return (
        (0x3000 <= c <= 0x30FF)  # CJK punctuation, hiragana, katakana
        or (0x3400 <= c <= 0x9FFF)  # CJK unified ideographs (+ ext A)
        or (0xF900 <= c <= 0xFAFF)  # CJK compatibility ideographs
        or (0xFF00 <= c <= 0xFFEF)  # fullwidth forms
    )


def split_atoms(text: str) -> list[str]:
    """lib/atoms.ts:16-27 splitAtoms(). Each CJK character becomes its own atom, each
    whitespace character becomes its own atom (despite the Node comment saying "each run
    of whitespace" — the actual Node code buffers whitespace one character at a time, same
    as here), and runs of everything else (Latin words, digits, punctuation, emoji) stay
    together as one atom."""
    atoms: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf:
            atoms.append(buf)
            buf = ""

    for ch in text:
        if is_cjk(ch):
            flush()
            atoms.append(ch)
        elif _WHITESPACE_RE.match(ch):
            flush()
            atoms.append(ch)
        else:
            buf += ch
    flush()
    return atoms


def text_width(width_of: WidthOf, text: str, size: float, weight: float, font: FontFamily = "sans") -> float:
    """lib/atoms.ts:30-34 textWidth(): the sum of the text's atoms' measured widths."""
    return sum(width_of(atom, size, weight, font) for atom in split_atoms(text))
