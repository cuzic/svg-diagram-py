"""1:1 port of lib/wordart-vertical.ts — vertical text (縦書き): splits a column of text into
units and sets them in columns, right to left.

Approximation note: Node's `graphemes()` uses `Intl.Segmenter('ja', {granularity: 'grapheme'})`
to cluster combining marks / emoji ZWJ sequences / regional-indicator flag pairs into single
"characters a person sees". Python's stdlib has no equivalent (no Unicode Text Segmentation /
UAX #29 implementation without a third-party package), so this splits by Unicode code point
instead (`list(text)`), matching Node exactly for plain CJK/Latin headline text (the vast
majority of wordart() usage) but not for text containing combining marks or multi-codepoint
emoji. Same stdlib-only tradeoff as approx_width.py.

Golden master: lib/wordart-vertical.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import re

from .atoms import text_width
from .tokens import MIN_FONT_SIZE

COLUMN_PITCH = 1.4  # lib/wordart-vertical.ts:12
BASELINE = 0.36  # lib/wordart-vertical.ts:13

ROTATED: frozenset[str] = frozenset("ー―—‐－…‥⋯〜～（）［］｛｝「」『』【】〔〕〈〉《》〝〟")
HANG: frozenset[str] = frozenset("、。，．")
MAX_CARRY = 2
NO_START: frozenset[str] = frozenset("）］｝」』】〕〉》！？ー〜～…‥ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ・：；")
NOT_LAST: frozenset[str] = frozenset("（［｛「『【〔〈《〝")
PUNCT: frozenset[str] = frozenset("、。，．")
SMALL: frozenset[str] = frozenset("ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ")

# lib/wordart-vertical.ts:38 ASCII_RUN — the `(?!\p{M})` trailing guard (don't stop a run right
# before a combining mark) is not replicated: stdlib `re` has no Unicode property escapes.
ASCII_RUN = re.compile(r"^[\x21-\x7e]+(?: +[\x21-\x7e]+)*")
_DIGITS_1_2 = re.compile(r"^\d{1,2}$")


def graphemes(text: str) -> list[str]:
    """lib/wordart-vertical.ts:27 graphemes() — approximated by code point, see module docstring."""
    return list(text)


def tokenize_column(text: str) -> list[dict]:
    """lib/wordart-vertical.ts:41-60 tokenizeColumn(). Splits one column of text (no newline)
    into tokens: {"kind": "glyph", "ch", "dx", "dy", "turn"} | {"kind": "tcy", "text"} |
    {"kind": "side", "text"} | {"kind": "blank"}."""
    out: list[dict] = []
    rest = text
    while rest:
        m = ASCII_RUN.match(rest)
        if m:
            s = m.group(0)
            out.append({"kind": "tcy", "text": s} if _DIGITS_1_2.match(s) else {"kind": "side", "text": s})
            rest = rest[len(s) :]
            continue
        ch = graphemes(rest)[0]
        rest = rest[len(ch) :]
        if ch == " " or ch == "　":
            out.append({"kind": "blank"})
        elif ch in ROTATED:
            out.append({"kind": "glyph", "ch": ch, "dx": 0, "dy": 0, "turn": True})
        elif ch in PUNCT:
            out.append({"kind": "glyph", "ch": ch, "dx": 0.5, "dy": -0.5, "turn": False})
        elif ch in SMALL:
            out.append({"kind": "glyph", "ch": ch, "dx": 0.1, "dy": -0.1, "turn": False})
        else:
            out.append({"kind": "glyph", "ch": ch, "dx": 0, "dy": 0, "turn": False})
    return out


def tcy_size(size: float) -> float:
    """lib/wordart-vertical.ts:63 tcySize()."""
    from .emit_common import js_round

    return min(size, max(MIN_FONT_SIZE, js_round(size * 0.8)))


def vertical_columns(text: str, size: float, weight: float, width_of, *, limit: float | None = None, spacing: float = 0, font: str = "sans") -> list[dict]:
    """lib/wordart-vertical.ts:73-116 verticalColumns(). Returns a list of
    {"cells": [{"token", "top", "len"}, ...], "len"} — columns[0] is the rightmost."""
    from .emit_common import js_round

    def settle(t: dict) -> dict:
        if t["kind"] == "side":
            return {"token": t, "len": text_width(width_of, t["text"], size, weight, font)}
        if t["kind"] == "tcy":
            if text_width(width_of, t["text"], tcy_size(size), weight, font) <= size + 0.5:
                return {"token": t, "len": size}
            return settle({"kind": "side", "text": t["text"]})
        return {"token": t, "len": size}

    def name_of(t: dict) -> str:
        return t["ch"] if t["kind"] == "glyph" else (" " if t["kind"] == "blank" else t["text"])

    def end_of(cells: list[dict]) -> float:
        return (cells[-1]["top"] + cells[-1]["len"]) if cells else 0

    def stacked(tokens: list[dict]) -> list[dict]:
        cells: list[dict] = []
        for t in tokens:
            cells.append({"token": t["token"], "top": (end_of(cells) + spacing) if cells else 0, "len": t["len"]})
        return cells

    def is_glyph(t: dict, charset: frozenset) -> bool:
        return t["kind"] == "glyph" and t["ch"] in charset

    def no_start(t: dict) -> bool:
        return is_glyph(t, NO_START) or is_glyph(t, HANG)

    columns: list[dict] = []
    for para in text.split("\n"):
        cells: list[dict] = []
        hung = False

        def fits(l: float) -> bool:
            return limit is None or ((end_of(cells) + spacing) if cells else 0) + l <= limit + 0.5

        for raw in tokenize_column(para):
            settled = settle(raw)
            token, l = settled["token"], settled["len"]
            hangs = False
            if cells and not fits(l):
                if no_start(token) and not hung:
                    hung = hangs = True
                else:
                    carry: list[dict] = []
                    while len(cells) > 1 and (
                        (len(carry) < MAX_CARRY and no_start(carry[0]["token"] if carry else token)) or is_glyph(cells[-1]["token"], NOT_LAST)
                    ):
                        carry.insert(0, cells.pop())
                    if all(is_glyph(c["token"], NOT_LAST) for c in cells):
                        cells.extend(carry)
                        carry = []
                    columns.append({"cells": cells, "len": end_of(cells)})
                    cells = stacked([{"token": c["token"], "len": c["len"]} for c in carry])
                    hung = False
            if not hangs and not fits(l):
                assert limit is not None  # fits() always returns True when limit is None, so this block implies limit is not None
                if cells and no_start(token) and not hung:
                    hung = True
                elif limit is not None and l <= limit + 0.5 and cells:
                    pass
                else:
                    before = f" (with what goes before it, {js_round(end_of(cells) + spacing + l)}px)" if cells else ""
                    raise ValueError(f'wordart(): "{name_of(token)}" is {js_round(l)}px long but a column may be {js_round(limit)}px{before}: raise limit or shorten the word')
            cells.append({"token": token, "top": (end_of(cells) + spacing) if cells else 0, "len": l})
        columns.append({"cells": cells, "len": end_of(cells)})
    return columns
