"""Golden-master tests for box() extensions: stamp, tag, step badge, raw()."""

import pytest

from svg_diagram.emit_boxes import render_raw, render_stamp, render_step_badge, render_tag
from svg_diagram.tokens import ROLES

STAMP_CASES = [
    {"x": 10, "y": 20, "w": 100, "h": 50, "stamp": "draft", "stampW": 60},
    {"x": 0, "y": 0, "w": 200, "h": 80, "stamp": "最終", "stampW": 48},
]


@pytest.mark.parametrize("case", STAMP_CASES, ids=lambda c: str(c))
def test_render_stamp_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "renderStamp", **case})
    py_result = render_stamp(x=case["x"], y=case["y"], w=case["w"], h=case["h"], stamp=case["stamp"], stamp_w=case["stampW"], note_size=ROLES["note"])
    assert py_result == node_result


def test_render_stamp_empty_when_no_stamp():
    assert render_stamp(x=0, y=0, w=10, h=10, stamp=None, stamp_w=None, note_size=14) == ""


TAG_CASES = [
    {"x": 60, "y": 10, "w": 40, "h": 24, "tag": "NEW", "tagTone": "danger"},
    {"x": 60, "y": 10, "w": 40, "h": 24, "tag": "済", "tagTone": "muted"},
    {"x": 60, "y": 10, "w": 60, "h": 24, "tag": "default", "tone": "solid"},
]


@pytest.mark.parametrize("case", TAG_CASES, ids=lambda c: str(c))
def test_render_tag_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "renderTag", **case})
    py_result = render_tag(
        tag_box={"x": case["x"], "y": case["y"], "w": case["w"], "h": case["h"]},
        tag=case["tag"],
        tag_tone=case.get("tagTone"),
        tone=case.get("tone"),
        dim=case.get("dim", False),
    )
    assert py_result == node_result


STEP_CASES = [
    {"x": 10, "y": 20, "padX": 20, "padY": 16, "lineY0": 15, "step": 1, "tone": "accent"},
    {"x": 0, "y": 0, "padX": 20, "padY": 16, "lineY0": 15, "step": 12, "tone": "solid"},
]


@pytest.mark.parametrize("case", STEP_CASES, ids=lambda c: str(c))
def test_render_step_badge_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "renderStepBadge", **case})
    title_baseline_y = case["y"] + case["padY"] + case["lineY0"]
    py_result = render_step_badge(x=case["x"], pad_x=case["padX"], title_baseline_y=title_baseline_y, step=case["step"], tone=case.get("tone"))
    assert py_result == node_result


RAW_CASES = [
    {"x": 0, "y": 0, "w": 100, "h": 100, "tone": "accent"},
    {"x": 0, "y": 0, "w": 100, "h": 100, "tone": "accent-soft"},
    {"x": 0, "y": 0, "w": 100, "h": 100, "tone": "danger"},
]


@pytest.mark.parametrize("case", RAW_CASES, ids=lambda c: str(c))
def test_render_raw_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "renderRaw", **case})

    def draw(ctx):
        return f'<circle cx="50" cy="50" r="10" fill="{ctx["color"](case["tone"])}"/>'

    py_result = render_raw(x=case["x"], y=case["y"], w=case["w"], h=case["h"], day=1, draw=draw)
    assert py_result == node_result
