"""Golden-master tests for word_art_band()/layout_word_art()/render_word_art() against Node's
wordartBand()/layoutWordArt()/renderWordArt() (all exported — live-tested via the shared dummy
width function, same technique as test_flow_shapes.py).

`uid` (and anything derived from it: gradient ids, clip-path ids) is intentionally excluded
from the comparison — see wordart_look.py's `_hash36()` docstring for why."""

import pytest

from svg_diagram.wordart import layout_word_art, render_word_art, word_art_band

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}

GEOMETRY_KEYS = ("x", "y", "w", "h", "size", "writing", "text", "look", "items", "local", "plate", "reflection", "anchors", "labelBoxes")


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


def _assert_matches(py_result: dict, node_result: dict) -> None:
    for key in GEOMETRY_KEYS:
        assert py_result.get(key) == node_result.get(key), key


LAYOUT_CASES = [
    {"text": "ハロー", "opts": {}},
    {"text": "Hello", "opts": {"style": "outline", "arc": 30}},
    {"text": "縦書き", "opts": {"writing": "vertical"}},
    {"text": "光", "opts": {"style": "glow"}},
    {"text": "立体", "opts": {"style": "3d", "rotate": 15}},
    {"text": "映り込み", "opts": {"reflection": True}},
    {"text": "にじみ", "opts": {"gradient": {"from": "accent", "to": "danger"}, "plate": "soft", "flip": "horizontal"}},
    {"text": "凹凸", "opts": {"style": "emboss"}},
    {"text": "ステッカー", "opts": {"style": "sticker"}},
    {"text": "影", "opts": {"shadow": {"dx": 10, "dy": 5}}},
    {"text": "両方反転", "opts": {"flip": "both", "rotate": 45}},
    {"text": "ながいながい縦書きのテキストです", "opts": {"writing": "vertical", "limit": 200}},
    {"text": "折り返しテストする長い文章です", "opts": {"size": 28}, "cw": 200},
    {"text": "中抜き", "opts": {"tone": "none", "outline": True}},
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["text"])
def test_layout_word_art_matches_node(node_golden, case):
    cw = case.get("cw", 600)
    node_result = node_golden.call({"kind": "layoutWordArt", "text": case["text"], "x": 0, "y": 0, "cw": cw, "opts": case["opts"]})
    band = word_art_band(case["text"], **case["opts"])
    py_result = layout_word_art(band, 0, 0, cw, _width_of, ROLES, "phrase")
    _assert_matches(py_result, node_result)


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["text"])
def test_render_word_art_matches_node(node_golden, case):
    cw = case.get("cw", 600)
    band = word_art_band(case["text"], **case["opts"])
    laid = layout_word_art(band, 0, 0, cw, _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderWordArt", "band": laid})
    py_result = render_word_art(laid)
    assert py_result == node_result


def test_arc_rejects_single_character():
    with pytest.raises(ValueError):
        word_art_band("A", arc=30)


def test_arc_rejects_vertical():
    with pytest.raises(ValueError):
        word_art_band("AB", arc=30, writing="vertical")


def test_empty_text_rejected():
    with pytest.raises(ValueError):
        word_art_band("   ")
