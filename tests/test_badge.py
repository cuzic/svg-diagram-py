"""Golden-master tests for badge_svg()/pill_svg() against Node's badgeSvg()/pillSvg()."""

import pytest

from svg_diagram.badge import pill_svg
from svg_diagram.emit_common import escape_xml, snap4

BADGE_CASES = [
    {"cx": 50, "cy": 50, "shape": "circle", "r": 11, "w": 22, "label": "1", "aria": "手順 1", "size": 14, "fill": "#a8632b"},
    {"cx": 50, "cy": 50, "shape": "circle", "r": 11, "w": 22, "label": "12", "aria": "手順 12", "size": 14, "fill": "#1f6e73"},
    {"cx": 50, "cy": 50, "shape": "circle", "r": 11, "w": 40, "label": "123", "aria": "手順 123", "size": 14, "fill": "#b91c1c"},
    {"cx": 50, "cy": 50, "shape": "square", "r": 11, "w": 30, "label": "A", "aria": "A", "size": 14, "fill": "#22201b"},
    {"cx": 50, "cy": 50, "shape": "triangle", "r": 11, "w": 22, "label": "!", "aria": "警告", "size": 14, "fill": "#b91c1c"},
    {"cx": 50, "cy": 50, "shape": "circle", "r": 11, "w": 22, "label": "", "aria": "no label", "size": 14, "fill": "#ffffff", "stroke": "#22201b"},
    {"cx": 50, "cy": 50, "shape": "circle", "r": 11, "w": 22, "label": "1", "aria": "手順 1", "size": 14, "fill": "#a8632b", "baseline": 72},
    {"cx": 50, "cy": 50, "shape": "circle", "r": 11, "w": 22, "label": "1", "aria": "手順 1", "size": 14, "fill": "#a8632b", "weight": 400, "text": "#ffffff"},
]


@pytest.mark.parametrize("case", BADGE_CASES, ids=lambda c: str(c))
def test_badge_svg_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "badgeSvg", **case})

    from svg_diagram.badge import badge_svg

    py_result = badge_svg(
        cx=case["cx"],
        cy=case["cy"],
        shape=case["shape"],
        r=case["r"],
        w=case["w"],
        label=case["label"],
        aria=case["aria"],
        size=case["size"],
        weight=case.get("weight", 700),
        fill=case["fill"],
        stroke=case.get("stroke"),
        sw=case.get("sw", 2),
        text=case.get("text"),
        baseline=case.get("baseline"),
        snap=snap4,
        esc=escape_xml,
    )
    assert py_result == node_result


PILL_CASES = [
    {"x": 10, "y": 10, "w": 40, "h": 24, "fill": "#ffffff", "stroke": "#22201b", "cx": 30, "baseline": 27, "textColor": "#22201b", "size": 14, "labelHtml": "OK"},
    {"x": 10, "y": 10, "w": 60, "h": 24, "fill": "#a8632b", "cx": 40, "baseline": 27, "textColor": "#ffffff", "size": 14, "weight": 400, "labelHtml": "tag"},
    {"x": 10, "y": 14, "w": 40, "h": 24, "fill": "#ffffff", "stroke": "#6f6659", "dash": "4 3", "cx": 30, "baseline": 30, "textColor": "#22201b", "size": 14, "labelHtml": "draft", "rawY": 10},
]


@pytest.mark.parametrize("case", PILL_CASES, ids=lambda c: str(c))
def test_pill_svg_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "pillSvg", **case})
    py_result = pill_svg(
        x=case["x"],
        y=case["y"],
        w=case["w"],
        h=case["h"],
        fill=case["fill"],
        stroke=case.get("stroke"),
        sw=case.get("sw", 2),
        dash=case.get("dash"),
        cx=case["cx"],
        baseline=case["baseline"],
        text=case["textColor"],
        size=case["size"],
        weight=case.get("weight", 700),
        label_html=case["labelHtml"],
        raw_y=case.get("rawY"),
    )
    assert py_result == node_result
