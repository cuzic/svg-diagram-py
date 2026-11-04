"""1:1 port of the text-measurement helpers in lib/tree.ts that don't depend on the tree
auto-layout engine: measureNode()/nodeRuns()/katakanaWidth(). Shared by cloud() (this port)
and, later, tree()/mindmap().

Golden master: lib/tree.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
import re

from .atoms import split_atoms, text_width
from .wrap import WrapMode, longest_unit_width, wrap_text

PAD_X, PAD_Y, MIN_W = 14, 8, 88
KEEP_WORDS_CAP = 240
_KATAKANA_RE = re.compile(r"[ァ-ヿｦ-ﾟ]+")


def line_h(size: float) -> int:
    from .emit_common import js_round

    return js_round(size * 1.4)


def katakana_width(text: str, width_of, size: float, weight: int) -> float:
    """lib/tree.ts:47-50 katakanaWidth()."""
    widest = 0.0
    for run in _KATAKANA_RE.findall(text):
        w = sum(width_of(a, size, weight, "sans") for a in split_atoms(run))
        widest = max(widest, w)
    return widest


def measure_node(label: str, sub: str | None, max_w: float, width_of, roles: dict, mode: WrapMode, floor: bool, keep_words_cap: float | None = None, keep_words: bool | None = None) -> dict:
    """lib/tree.ts:55-70 measureNode()."""
    L, S = roles["body"], roles["note"]
    inner = max_w - 2 * PAD_X
    if floor and keep_words is not False:
        word = max(katakana_width(label, width_of, L, 700), katakana_width(sub, width_of, S, 400) if sub else 0)
        inner = max(inner, min(math.ceil(word), keep_words_cap if keep_words_cap is not None else KEEP_WORDS_CAP))
    if mode == "bunsetsu":
        unit = max(
            longest_unit_width(split_atoms(label), lambda a: width_of(a, L, 700, "sans"), mode),
            longest_unit_width(split_atoms(sub), lambda a: width_of(a, S, 400, "sans"), mode) if sub else 0,
        )
        inner = max(inner, min(math.ceil(unit), math.floor(1.5 * max_w) - 2 * PAD_X))
    lab = wrap_text(label, max_width=inner, atom_width=lambda a: width_of(a, L, 700, "sans"), mode=mode)
    sb = wrap_text(sub, max_width=inner, atom_width=lambda a: width_of(a, S, 400, "sans"), mode=mode) if sub else []
    widths = [text_width(width_of, l, L, 700) for l in lab] + [text_width(width_of, l, S, 400) for l in sb]
    tw = max(widths) if widths else 0
    return {"label": lab, "sub": sb, "w": max(MIN_W, math.ceil(tw + 2 * PAD_X)), "h": 2 * PAD_Y + len(lab) * line_h(L) + len(sb) * line_h(S)}


_WS_RE = re.compile(r"\s")


def narrow_texts(texts: list[list[str]]) -> list[str]:
    """lib/tree.ts:38-39 narrowTexts(): the wrapped texts (each a list of lines) that broke into
    several lines of 2.5 characters or fewer on average — what `fit: 'shrink'` squeezing a column
    too far does (rule shrink-narrow-text). Returns the joined texts, each once. Shared by bpmn()
    (this port) and, later, states()."""
    out: list[str] = []
    for lines in texts:
        if len(lines) >= 3 and len(_WS_RE.sub("", "".join(lines))) / len(lines) <= 2.5:
            joined = "".join(lines)
            if joined not in out:
                out.append(joined)
    return out


def narrow_field(texts: list[list[str]]) -> dict:
    """lib/tree.ts:43 narrowField()."""
    n = narrow_texts(texts)
    return {"narrow": n} if n else {}


def node_runs(r: dict, l: dict, roles: dict) -> list[dict]:
    """lib/tree.ts:73-79 nodeRuns(): the centred text runs of a node laid in rectangle r."""
    L, S = roles["body"], roles["note"]
    out = []
    ty = r["y"] + PAD_Y
    for line in l["label"]:
        out.append({"text": line, "x": r["x"] + r["w"] / 2, "y": ty + L, "size": L, "bold": True, "muted": False})
        ty += line_h(L)
    for line in l["sub"]:
        out.append({"text": line, "x": r["x"] + r["w"] / 2, "y": ty + S, "size": S, "bold": False, "muted": True})
        ty += line_h(S)
    return out
