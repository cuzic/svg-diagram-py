"""Golden-master tests for render_box_rect() against Node's renderBoxRect()."""

import pytest

from svg_diagram.emit_boxes import render_box_rect

CASES = [
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "accent"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "plain"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "new"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "changed"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "removed"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "muted"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "danger"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "solid"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "solid-danger"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "danger", "dashed": False},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "accent", "dashed": True},
    {"x": 10, "y": 20, "w": 100, "h": 50, "dim": True},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "accent", "dim": True},
    {"x": 10, "y": 20, "w": 100, "h": 50, "dataNode": "n1"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "ok"},  # alias -> accent
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "warn"},  # alias -> danger
    {"x": 10, "y": 20, "w": 100, "h": 50, "tone": "off"},  # alias -> muted
    {"x": 10, "y": 20, "w": 100, "h": 50, "day": 2, "tone": "accent"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "day": "blue", "tone": "accent"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "day": "teal", "tone": "accent"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "day": "amber", "tone": "accent"},
    {"x": 10, "y": 20, "w": 100, "h": 50, "day": "blue", "tone": "muted"},  # doc theme: full-contrast stroke, not slideStroke
    # snap4 asymmetry: snap4(x+w)-snap4(x) must NOT equal snap4(w) when neither is a multiple of 4
    {"x": 1, "y": 2, "w": 101, "h": 51},
    {"x": 3, "y": 7, "w": 97, "h": 53, "tone": "muted"},
    {"x": 0, "y": 0, "w": 1, "h": 1},
    {"x": -5, "y": -3, "w": 50, "h": 30},
    {"x": 2.5, "y": 2.5, "w": 99.5, "h": 49.5},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_render_box_rect_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "box", **case})
    py_result = render_box_rect(
        x=case["x"],
        y=case["y"],
        w=case["w"],
        h=case["h"],
        day=case.get("day", 1),
        tone=case.get("tone"),
        dashed=case.get("dashed"),
        dim=case.get("dim", False),
        data_node=case.get("dataNode"),
    )
    assert py_result == node_result
