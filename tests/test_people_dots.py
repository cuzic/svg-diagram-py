"""Golden-master tests for layout_people()/layout_dots() (both exported in Node, live-tested
via a shared dummy width function — see golden/emit_cli.ts's peopleWidthOf) and
render_people()/render_dots()."""

import pytest

from svg_diagram.people_dots import layout_dots, layout_people, render_dots, render_people

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _people_width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


PEOPLE_CASES = [
    {"cols": 5, "size": 24, "gap": 4, "total": 10, "count": 6, "x": 0, "y": 0, "cw": 400},
    {"cols": 5, "size": 24, "gap": 4, "total": 10, "count": 4, "count2": 3, "x": 0, "y": 0, "cw": 400},
    {"cols": 3, "size": 24, "gap": 4, "total": 7, "count": 7, "x": 0, "y": 0, "cw": 400, "align": "left"},
    {"cols": 10, "size": 20, "gap": 4, "total": 42, "count": 30, "x": 0, "y": 0, "cw": 500, "side": {"value": "42人", "label": "対象"}},
]


@pytest.mark.parametrize("case", PEOPLE_CASES, ids=lambda c: str(c))
def test_layout_people_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutPeople", **case})
    py_result = layout_people(
        cols=case["cols"], size=case["size"], gap=case["gap"], total=case["total"], count=case["count"],
        count2=case.get("count2", 0), x=case["x"], y=case["y"], cw=case["cw"], width_of=_people_width_of,
        align=case.get("align"), side=case.get("side"), roles=ROLES,
    )
    assert py_result["x"] == node_result["x"]
    assert py_result["y"] == node_result["y"]
    assert py_result["w"] == node_result["w"]
    assert py_result["h"] == node_result["h"]
    assert py_result["icons"] == node_result["icons"]
    assert py_result["texts"] == node_result["texts"]


DOTS_CASES = [
    {"r": 5, "dots": [{"at": 10}, {"at": 50}, {"at": 90}], "zones": [], "min": 0, "max": 100, "x": 0, "y": 0, "cw": 300},
    {"r": 5, "dots": [{"at": 10}, {"at": 12}, {"at": 90}], "zones": [{"from": 0, "to": 30, "tone": "muted", "label": "低"}], "min": 0, "max": 100, "x": 0, "y": 0, "cw": 300},
    {"r": 6, "dots": [{"at": 20, "tone": "danger"}], "zones": [], "min": 0, "max": 100, "x": 0, "y": 0, "cw": 300, "lowLabel": "少", "highLabel": "多"},
]


@pytest.mark.parametrize("case", DOTS_CASES, ids=lambda c: str(c))
def test_layout_dots_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutDots", **case})
    py_result = layout_dots(
        r=case["r"], dots=case["dots"], zones=case["zones"], min_val=case["min"], max_val=case["max"],
        x=case["x"], y=case["y"], cw=case["cw"], width_of=_people_width_of,
        low_label=case.get("lowLabel"), high_label=case.get("highLabel"), roles=ROLES,
    )
    assert py_result["x"] == node_result["x"]
    assert py_result["w"] == node_result["w"]
    assert py_result["axis"] == node_result["axis"]
    assert py_result["dots"] == node_result["dots"]
    assert py_result["zones"] == node_result["zones"]
    assert py_result["texts"] == node_result["texts"]


def test_render_people_matches_node(node_golden):
    icons = [{"x": 0, "y": 0, "on": True}, {"x": 28, "y": 0, "on": False}]
    texts = [{"text": "2人", "x": 60, "y": 15, "size": 15, "bold": True}]
    node_result = node_golden.call({"kind": "renderPeople", "x": 0, "y": 0, "size": 24, "icons": icons, "texts": texts, "tone": "accent", "tone2": "danger", "rest": "muted", "alt": "2人中1人"})
    py_result = render_people(x=0, y=0, size=24, icons=icons, texts=texts, tone="accent", tone2="danger", rest="muted", alt="2人中1人")
    assert py_result == node_result


def test_render_dots_matches_node(node_golden):
    axis = {"x1": 10, "x2": 290, "y": 28}
    zones = [{"x": 10, "w": 80, "y": 28, "tone": "muted", "top": 8}]
    dots = [{"x": 40, "y": 12, "tone": "accent"}]
    texts = [{"text": "少", "x": 10, "y": 32, "anchor": "start", "size": 14}]
    node_result = node_golden.call({"kind": "renderDots", "axis": axis, "zones": zones, "dots": dots, "texts": texts, "r": 5, "alt": "分布"})
    py_result = render_dots(axis=axis, zones=zones, dots=dots, texts=texts, r=5, alt="分布")
    assert py_result == node_result
