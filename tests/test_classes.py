"""Golden-master tests for classes_band()/layout_classes_band()/render_classes() against
Node's classDiagram()/layoutClassesBand()/renderClasses() (all exported — live-tested via
the shared dummy width function, same technique as test_bpmn.py). Depends on the now-ported
layered_route.py (layered_attempt) and fit_width.py (fit_layout/plan_fit)."""

from __future__ import annotations

import pytest

from svg_diagram.classes import classes_band, layout_classes_band, render_classes

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


SIMPLE_CLASSES = [
    {"id": "animal", "name": "Animal", "abstract": True, "methods": ["speak()"]},
    {"id": "dog", "name": "Dog", "attrs": ["name: string"], "methods": ["speak()", "fetch()"]},
    {"id": "cat", "name": "Cat", "attrs": ["name: string"]},
]
SIMPLE_RELATIONS = [
    {"from": "dog", "to": "animal", "kind": "inherit"},
    {"from": "cat", "to": "animal", "kind": "inherit"},
    {"from": "dog", "to": "cat", "kind": "assoc", "label": "chases", "toMult": "0..1"},
]

# a self-loop (recursive association) plus a compose/aggregate pair and a stereotype
LOOP_CLASSES = [
    {"id": "node", "name": "Node", "stereotype": "entity", "attrs": ["value: T"]},
    {"id": "tree", "name": "Tree", "attrs": ["root: Node"]},
    {"id": "forest", "name": "Forest"},
]
LOOP_RELATIONS = [
    {"from": "node", "to": "node", "label": "next", "fromMult": "1", "toMult": "0..1"},
    {"from": "tree", "to": "node", "kind": "compose", "fromMult": "1", "toMult": "1..*"},
    {"from": "forest", "to": "tree", "kind": "aggregate", "label": "contains"},
]

# a dependency + an open arrow, tone set on a class
DEPEND_CLASSES = [
    {"id": "service", "name": "Service", "tone": "accent"},
    {"id": "repo", "name": "Repo"},
    {"id": "util", "name": "Util"},
]
DEPEND_RELATIONS = [
    {"from": "service", "to": "repo", "kind": "depend"},
    {"from": "service", "to": "util", "kind": "arrow", "label": "uses"},
]

LAYOUT_CASES = [
    {"id": "simple-inherit-assoc", "classes": SIMPLE_CLASSES, "relations": SIMPLE_RELATIONS, "opts": {}, "w": 700},
    {"id": "simple-dir-right", "classes": SIMPLE_CLASSES, "relations": SIMPLE_RELATIONS, "opts": {"dir": "right"}, "w": 900},
    {"id": "simple-dir-auto", "classes": SIMPLE_CLASSES, "relations": SIMPLE_RELATIONS, "opts": {"dir": "auto"}, "w": 900},
    {"id": "loop-compose-aggregate-right", "classes": LOOP_CLASSES, "relations": LOOP_RELATIONS, "opts": {"dir": "right"}, "w": 900},
    {"id": "loop-compose-aggregate-down", "classes": LOOP_CLASSES, "relations": LOOP_RELATIONS, "opts": {}, "w": 700},
    {"id": "depend-arrow-tone", "classes": DEPEND_CLASSES, "relations": DEPEND_RELATIONS, "opts": {}, "w": 700},
    {"id": "straighten-false", "classes": SIMPLE_CLASSES, "relations": SIMPLE_RELATIONS, "opts": {"straighten": False}, "w": 700},
    {"id": "with-id", "classes": SIMPLE_CLASSES, "relations": SIMPLE_RELATIONS, "opts": {"id": "diag1"}, "w": 700},
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_layout_classes_band_matches_node(node_golden, case):
    req: dict = {"kind": "layoutClassesBand", "classes": case["classes"], "relations": case["relations"], "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]}
    node_result = node_golden.call(req)
    band = classes_band(case["classes"], case["relations"], dir=case["opts"].get("dir"), straighten=case["opts"].get("straighten"), id=case["opts"].get("id"))
    env = {"wrap": "phrase", "keepWords": False}
    py_result = layout_classes_band(band, 0, 0, case["w"], _width_of, ROLES, env)
    assert py_result == node_result


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_render_classes_matches_node(node_golden, case):
    band = classes_band(case["classes"], case["relations"], dir=case["opts"].get("dir"), straighten=case["opts"].get("straighten"), id=case["opts"].get("id"))
    env = {"wrap": "phrase", "keepWords": False}
    laid = layout_classes_band(band, 0, 0, case["w"], _width_of, ROLES, env)
    node_result = node_golden.call({"kind": "renderClasses", "band": laid})
    py_result = render_classes(laid)
    assert py_result == node_result


def test_classes_rejects_no_classes():
    with pytest.raises(ValueError):
        classes_band([], [])


def test_classes_rejects_bad_dir():
    with pytest.raises(ValueError):
        classes_band(SIMPLE_CLASSES, [], dir="up")


def test_classes_rejects_duplicate_id():
    with pytest.raises(ValueError):
        band = classes_band([{"id": "a"}, {"id": "a"}], [])
        layout_classes_band(band, 0, 0, 500, _width_of, ROLES, {"wrap": "phrase", "keepWords": False})


def test_classes_rejects_unknown_relation_target():
    with pytest.raises(ValueError):
        band = classes_band([{"id": "a"}], [{"from": "a", "to": "nope"}])
        layout_classes_band(band, 0, 0, 500, _width_of, ROLES, {"wrap": "phrase", "keepWords": False})


def test_classes_rejects_bad_relation_kind():
    with pytest.raises(ValueError):
        band = classes_band([{"id": "a"}, {"id": "b"}], [{"from": "a", "to": "b", "kind": "nope"}])
        layout_classes_band(band, 0, 0, 500, _width_of, ROLES, {"wrap": "phrase", "keepWords": False})


def test_classes_too_narrow_raises_fit_error():
    band = classes_band(SIMPLE_CLASSES, SIMPLE_RELATIONS, dir="down")
    with pytest.raises(ValueError):
        layout_classes_band(band, 0, 0, 50, _width_of, ROLES, {"wrap": "phrase", "keepWords": False})
