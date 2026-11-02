"""1:1 port of lib/wrap.ts — greedy line-wrapping over pre-measured break atoms,
with basic Japanese kinsoku shori (禁則処理). Pure algorithm; width comes from
an injected `atom_width` callback, same split as atoms.py.

JS/Python index-semantics trap this file is careful about: JS array access with
an out-of-range or negative index returns `undefined` (never wraps around),
whereas Python's `lst[-1]` wraps to the last element. Every place Node's code
could see `undefined` from an index at or below 0 uses `_at()` here instead of
a bare `[]`, to avoid accidentally reading from the end of the list.

Golden master: lib/wrap.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Literal, TypeVar

from .atoms import split_atoms

WrapMode = Literal["phrase", "char", "bunsetsu"]

# lib/wrap.ts:22-25
CANNOT_START_LINE: frozenset[str] = frozenset("、。，．・：；！？」』）〕】〉》ゝゞーぁぃぅぇぉっゃゅょァィゥェォッャュョ")
CANNOT_END_LINE: frozenset[str] = frozenset("「『（〔【〈《")
CLAUSE_END: frozenset[str] = frozenset("、。，．！？")

_WS_RE = re.compile(r"^\s+$")


def _at(lst: list, i: int):
    """Mimics JS `lst[i]`: out-of-range (including negative) is `undefined`, never wraps."""
    return lst[i] if 0 <= i < len(lst) else None


def is_whitespace(atom: str) -> bool:
    """lib/wrap.ts:27 isWhitespace()."""
    return bool(_WS_RE.match(atom))


def is_hiragana(atom: str) -> bool:
    """lib/wrap.ts:31 isHiragana()."""
    if len(atom) != 1:
        return False
    c = ord(atom)
    return 0x3041 <= c <= 0x309F


def script_run(atom: str) -> str:
    """lib/wrap.ts:57-63 scriptRun(): 'k' katakana (+ ー・ and half-width kana), 'h' kanji, '' otherwise."""
    if len(atom) != 1:
        return ""
    c = ord(atom)
    if (0x30A1 <= c <= 0x30FF) or (0xFF66 <= c <= 0xFF9F):
        return "k"
    if (0x4E00 <= c <= 0x9FFF) or (0x3400 <= c <= 0x4DBF) or c == 0x3005:
        return "h"
    return ""


@dataclass
class _TextAtom:
    text: str
    glue: bool = False


def run_glue_of(atoms: list, mode: WrapMode) -> list[bool]:
    """lib/wrap.ts:35-43 runGlueOf(). `atoms` elements need a `.text` attribute (or be a
    plain `_TextAtom`/styled-atom instance) — matches Node's duck-typed `{text}` access."""
    phrase = mode in ("phrase", "bunsetsu")
    out = []
    for i, a in enumerate(atoms):
        if not phrase or i == 0:
            out.append(False)
            continue
        prev = atoms[i - 1].text
        if script_run(a.text) != "" and script_run(a.text) == script_run(prev):
            out.append(True)
            continue
        out.append(mode == "bunsetsu" and is_hiragana(a.text) and not is_whitespace(prev) and prev != "\n" and prev not in CLAUSE_END)
    return out


def longest_unit_width(atoms: list[str], atom_width: Callable[[str], float], mode: WrapMode) -> float:
    """lib/wrap.ts:46-54 longestUnitWidth()."""
    glue = run_glue_of([_TextAtom(text) for text in atoms], mode)
    best = 0.0
    cur = 0.0
    for i, a in enumerate(atoms):
        if is_whitespace(a) or a == "\n":
            best = max(best, cur)
            cur = 0.0
            continue
        if glue[i]:
            cur += atom_width(a)
        else:
            best = max(best, cur)
            cur = atom_width(a)
    return max(best, cur)


A = TypeVar("A")


def wrap_styled_atoms(atoms: list[_TextAtom], *, max_width: float, atom_width: Callable[[_TextAtom], float], mode: WrapMode) -> list[list[_TextAtom]]:
    """lib/wrap.ts:69-163 wrapStyledAtoms(). `atoms` elements need `.text` and `.glue`
    attributes (use `_TextAtom`, or any object with those two fields — mirrors Node's
    duck-typed generic `<A extends {text, glue?}>`)."""
    lines: list[list[_TextAtom]] = []
    cur: list[_TextAtom] = []
    cur_width = 0.0
    hard_break_before_last = False
    last_line_start = 0
    run_glue = run_glue_of(atoms, mode)

    n = len(atoms)
    i = 0
    while i < n:
        atom = atoms[i]
        if atom.text == "\n":
            lines.append(cur)
            cur = []
            cur_width = 0.0
            hard_break_before_last = True
            i += 1
            continue
        if is_whitespace(atom.text):
            if len(cur) == 0:
                i += 1
                continue
            w = atom_width(atom)
            if cur_width + w <= max_width:
                cur.append(atom)
                cur_width += w
            else:
                lines.append(cur)
                cur = []
                cur_width = 0.0
            i += 1
            continue

        unit = [atom]
        j = i
        while j + 1 < n and (atoms[j + 1].glue or run_glue[j + 1]):
            j += 1
            unit.append(atoms[j])
        w = sum(atom_width(a) for a in unit)
        if w > max_width and j > i:
            for k in range(i + 1, j + 1):
                run_glue[k] = False
            j = i
            unit = [atom]
            while j + 1 < n and atoms[j + 1].glue:
                j += 1
                unit.append(atoms[j])
            w = sum(atom_width(a) for a in unit)
        start = i
        i = j

        if len(cur) == 0 or cur_width + w <= max_width:
            if len(cur) == 0:
                last_line_start = start
            cur.extend(unit)
            cur_width += w
        elif atom.text in CANNOT_START_LINE:
            cut = next((k for k in range(1, len(unit)) if not unit[k].glue), -1)
            if cut > 0:
                i = i - len(unit) + cut
                if i + 1 < n:
                    run_glue[i + 1] = False
                unit = unit[:cut]
            cur.extend(unit)
            cur_width += sum(atom_width(a) for a in unit)
        else:
            lines.append(cur)
            cur = unit
            cur_width = w
            last_line_start = start
            hard_break_before_last = False
        i += 1

    if cur:
        lines.append(cur)
    run_glued = {id(a) for k, a in enumerate(atoms) if run_glue[k]}

    # An orphan: the wrap left a single character alone on the last line. Bring the last
    # character of the line above down with it (lib/wrap.ts:130-148).
    if len(lines) >= 2 and not hard_break_before_last:
        last, prev = lines[-1], lines[-2]
        solo = len(last) == 1 and len(last[0].text) == 1 and not is_whitespace(last[0].text) and not last[0].glue
        if solo:
            at = len(prev) - 1
            while at >= 0 and is_whitespace(prev[at].text):
                at -= 1
            sep = _at(atoms, last_line_start - 1)
            moved = _at(prev, at)
            gap = prev[at + 1 :] if at + 1 < len(prev) else []
            between = gap if gap else ([sep] if sep is not None and is_whitespace(sep.text) else [])
            if (
                moved is not None
                and at >= 2
                and not moved.glue
                and not (_at(prev, at + 1) and _at(prev, at + 1).glue)
                and id(moved) not in run_glued
                and prev[at - 1].text not in CANNOT_END_LINE
                and moved.text not in CANNOT_START_LINE
                and atom_width(moved) + sum(atom_width(a) for a in between) + atom_width(last[0]) <= max_width
            ):
                del prev[at:]
                last[0:0] = [moved, *between]

    # Second pass: an opening bracket stranded at a line's end gets pulled forward onto the
    # next line's start instead (lib/wrap.ts:150-159).
    for i in range(len(lines) - 1):
        line = lines[i]
        last = line[-1] if line else None
        if last is not None and len(line) > 1 and last.text in CANNOT_END_LINE:
            line.pop()
            lines[i + 1].insert(0, last)

    for line in lines:
        while line and is_whitespace(line[-1].text):
            line.pop()
    return lines


def wrap_atoms(atoms: list[str], *, max_width: float, atom_width: Callable[[str], float], mode: WrapMode) -> list[str]:
    """lib/wrap.ts:167-169 wrapAtoms()."""
    styled = [_TextAtom(text) for text in atoms]
    lines = wrap_styled_atoms(styled, max_width=max_width, atom_width=lambda a: atom_width(a.text), mode=mode)
    return ["".join(a.text for a in line).rstrip() for line in lines]


def wrap_text(text: str, *, max_width: float, atom_width: Callable[[str], float], mode: WrapMode) -> list[str]:
    """lib/wrap.ts:172-174 wrapText(): wraps a plain string, splitting it into atoms first."""
    return wrap_atoms(split_atoms(text), max_width=max_width, atom_width=atom_width, mode=mode)
