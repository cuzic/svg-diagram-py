"""Unit tests for wordart_vertical.py's tokenize_column()/tcy_size()/vertical_columns() — the
vertical-text (縦書き) kinsoku-shori (禁則処理) rules (hanging punctuation, carrying an
opening bracket across a column break, keeping an isolated bracket when nothing can carry it,
the too-long-for-any-column error) and the TCY (1-2 digit run set upright) fitting check, none
of which test_wordart_model.py's single smoke test (plain text, no `limit`) exercises — every
`limit`-driven branch in this file was previously untested.

Expected values are derived by hand from lib/wordart-vertical.ts (not by re-running the port),
so these catch divergence from the intended algorithm, not just regressions in the port.

`_width_of` makes a "side" (half-width/ASCII) run `len(text) * size` wide and leaves default
glyph cells at the fixed `size` per cell that settle() already gives them — same convention as
test_fta.py's dummy width function, just size-sensitive (needed for the TCY fit check below).
"""

from __future__ import annotations

import pytest

from svg_diagram.wordart_vertical import tcy_size, tokenize_column, vertical_columns


def _width_of(atom: str, size: float, weight: float, font: str) -> float:
    return len(atom) * size


def test_tokenize_column_ascii_runs_become_side_or_tcy():
    assert tokenize_column("AB") == [{"kind": "side", "text": "AB"}]
    assert tokenize_column("7") == [{"kind": "tcy", "text": "7"}]
    assert tokenize_column("12") == [{"kind": "tcy", "text": "12"}]
    assert tokenize_column("123") == [{"kind": "side", "text": "123"}]  # only a 1-2 digit run is tcy


def test_tokenize_column_special_character_classes():
    assert tokenize_column(" ") == [{"kind": "blank"}]
    assert tokenize_column("　") == [{"kind": "blank"}]
    assert tokenize_column("（") == [{"kind": "glyph", "ch": "（", "dx": 0, "dy": 0, "turn": True}]
    assert tokenize_column("。") == [{"kind": "glyph", "ch": "。", "dx": 0.5, "dy": -0.5, "turn": False}]
    assert tokenize_column("ゃ") == [{"kind": "glyph", "ch": "ゃ", "dx": 0.1, "dy": -0.1, "turn": False}]
    assert tokenize_column("金") == [{"kind": "glyph", "ch": "金", "dx": 0, "dy": 0, "turn": False}]


def test_tcy_size_clamps_between_80_percent_and_min_font_size_and_never_exceeds_size():
    assert tcy_size(25) == 20  # 25*0.8 = 20 exactly, within [MIN_FONT_SIZE, 25]
    assert tcy_size(15) == 14  # 15*0.8 = 12, clamped up to MIN_FONT_SIZE (14)
    assert tcy_size(10) == 10  # 10*0.8 = 8 -> clamped to 14, then clamped back down to size (10)


def test_vertical_columns_settles_a_short_digit_run_as_tcy_but_falls_back_for_a_longer_one():
    one_digit = vertical_columns("7", size=20, weight=400, width_of=_width_of)
    assert one_digit == [{"cells": [{"token": {"kind": "tcy", "text": "7"}, "top": 0, "len": 20}], "len": 20}]

    two_digit = vertical_columns("12", size=20, weight=400, width_of=_width_of)
    # 2 chars * tcy_size(20)=16 -> 32px, over size+0.5 (20.5): falls back to a side cell at `size`-width.
    assert two_digit == [{"cells": [{"token": {"kind": "side", "text": "12"}, "top": 0, "len": 40}], "len": 40}]


def test_vertical_columns_hangs_a_mark_that_may_not_start_a_column():
    # limit=25 fits one size-20 cell but not two; "。" (HANG) may not start the next column, so it
    # hangs below this one instead of breaking — the column ends up longer than `limit`.
    columns = vertical_columns("金。", size=20, weight=400, width_of=_width_of, limit=25)
    assert len(columns) == 1
    assert [c["token"]["ch"] for c in columns[0]["cells"]] == ["金", "。"]
    assert columns[0]["len"] == 40


def test_vertical_columns_keeps_an_isolated_opening_bracket_when_nothing_can_carry_it():
    # limit=25 fits only one cell at a time. "（" alone in its own column can't go with either
    # neighbour (an opening bracket may not end a column either), so it's kept by itself.
    columns = vertical_columns("金（木", size=20, weight=400, width_of=_width_of, limit=25)
    assert [[c["token"]["ch"] for c in col["cells"]] for col in columns] == [["金"], ["（"], ["木"]]


def test_vertical_columns_carries_an_opening_bracket_across_a_break():
    # limit=65 fits three size-20 cells (60) but not four (80). The 4th token forces a break;
    # the opening bracket (cells[-1]) may not end the first column, so it carries to the second.
    columns = vertical_columns("金木（木", size=20, weight=400, width_of=_width_of, limit=65)
    assert [[c["token"]["ch"] for c in col["cells"]] for col in columns] == [["金", "木"], ["（", "木"]]
    assert [col["len"] for col in columns] == [40, 40]


def test_vertical_columns_raises_when_a_token_is_too_long_for_any_column():
    with pytest.raises(ValueError, match=r'wordart\(\): " " is 20px long but a column may be 15px: raise limit'):
        vertical_columns(" ", size=20, weight=400, width_of=_width_of, limit=15)


def test_vertical_columns_raises_with_the_carried_context_when_it_tips_a_column_over():
    # Same break as the carry test above, but the 4th token is a long side-run that still
    # doesn't fit even alone with the carried bracket: the error names what came before it.
    with pytest.raises(ValueError, match=r"with what goes before it, 260px"):
        vertical_columns("金木（VERYLONGWORD", size=20, weight=400, width_of=_width_of, limit=65)
