"""Golden-master tests for escape_xml/escape_attr/emoji_span against Node."""

import pytest

from svg_diagram.emit_common import emoji_span, escape_attr, escape_xml

TEXTS = [
    "plain text",
    "a & b",
    "<tag>",
    'say "hi"',
    "a & b < c > d \"e\"",
    "日本語のラベル",
    "長いラベルテキストが続く場合のテストケースです。長いラベルテキストが続く場合のテストケースです。",
    "絵文字😀付きラベル",
    "⚠危険",
    "",
    "&&&<<<>>>\"\"\"",
]


@pytest.mark.parametrize("text", TEXTS)
def test_escape_xml_matches_node(node_golden, text):
    assert escape_xml(text) == node_golden.call({"kind": "escapeXml", "text": text})


@pytest.mark.parametrize("text", TEXTS)
def test_escape_attr_matches_node(node_golden, text):
    assert escape_attr(text) == node_golden.call({"kind": "escapeAttr", "text": text})


@pytest.mark.parametrize("text", TEXTS)
def test_emoji_span_matches_node(node_golden, text):
    assert emoji_span(text) == node_golden.call({"kind": "emojiSpan", "text": text})
