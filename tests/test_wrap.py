"""Golden-master tests for wrap_text() against Node's wrapText(), with the SAME trivial
width function (codepoint count) injected on both sides — see golden/emit_cli.ts's
`dummyWidthOf`. This tests the splitting/wrapping DECISION algorithm, not real pixel
widths (those come from HarfBuzz on the Node side and are approximated separately in
Python — see the plan's Phase A notes)."""

import pytest

from svg_diagram.wrap import wrap_text


def _dummy_width(atom: str) -> float:
    return len(atom)


CASES = [
    {"text": "hello world", "maxWidth": 5, "mode": "char"},
    {"text": "hello world foo bar", "maxWidth": 8, "mode": "char"},
    {"text": "日本語のテキストを折り返すテストです", "maxWidth": 6, "mode": "char"},
    {"text": "日本語のテキストを折り返すテストです", "maxWidth": 6, "mode": "phrase"},
    {"text": "日本語のテキストを折り返すテストです", "maxWidth": 6, "mode": "bunsetsu"},
    {"text": "これは、長い文章です。読点や句点の位置を確認します。", "maxWidth": 5, "mode": "char"},
    {"text": "カタカナのテストです", "maxWidth": 4, "mode": "phrase"},
    {"text": "「引用」の括弧のテスト", "maxWidth": 4, "mode": "char"},
    {"text": "一単語も入らないほど狭い", "maxWidth": 1, "mode": "char"},
    {"text": "a\nb\nc", "maxWidth": 10, "mode": "char"},
    {"text": "  leading and trailing  ", "maxWidth": 6, "mode": "char"},
    {"text": "", "maxWidth": 10, "mode": "char"},
    {"text": "verylongsingleword", "maxWidth": 5, "mode": "char"},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_wrap_text_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "wrapText", **case})
    py_result = wrap_text(case["text"], max_width=case["maxWidth"], atom_width=_dummy_width, mode=case["mode"])
    assert py_result == node_result
