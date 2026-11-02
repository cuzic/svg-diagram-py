"""Golden-master tests for graph_layout.py (layout_tree/layout_balanced) and map_layouts.py
(layout_hanging/layout_brace/layout_fishbone/layout_timeline_map/mirror) against Node's
lib/graph-layout.ts + lib/map-layouts.ts. All pure (no text metrics), so byte-identical."""

import pytest

from svg_diagram.graph_layout import layout_balanced, layout_tree
from svg_diagram.map_layouts import layout_brace, layout_fishbone, layout_hanging, layout_timeline_map, mirror


def _leaf(id_: str, w: float = 100, h: float = 40) -> dict:
    return {"id": id_, "size": {"w": w, "h": h}}


def _node(id_: str, children: list[dict], w: float = 100, h: float = 40) -> dict:
    return {"id": id_, "size": {"w": w, "h": h}, "children": children}


TREES = [
    _node("root", [_leaf("a"), _leaf("b"), _leaf("c")]),
    _node("root", [_node("a", [_leaf("a1"), _leaf("a2")]), _leaf("b")]),
    _leaf("solo"),
    _node("root", [_node("a", [_node("a1", [_leaf("a1a")])]), _leaf("b"), _node("c", [_leaf("c1"), _leaf("c2"), _leaf("c3")])]),
]


@pytest.mark.parametrize("tree", TREES, ids=lambda t: t["id"])
@pytest.mark.parametrize("dir_", ["down", "right"])
def test_layout_tree_matches_node(node_golden, tree, dir_):
    node_result = node_golden.call({"kind": "layoutTree", "root": tree, "dir": dir_})
    py_result = layout_tree(tree, dir=dir_)
    assert py_result["nodes"] == node_result["nodes"]
    assert py_result["edges"] == node_result["edges"]
    assert py_result["w"] == node_result["w"]
    assert py_result["h"] == node_result["h"]


BALANCED_TREES = [
    _node("root", [_leaf("a"), _leaf("b"), _leaf("c"), _leaf("d")], w=60, h=30),
    _node("root", [_node("a", [_leaf("a1"), _leaf("a2")]), _leaf("b"), _leaf("c")], w=60, h=30),
]


@pytest.mark.parametrize("tree", BALANCED_TREES, ids=lambda t: str(t))
def test_layout_balanced_matches_node(node_golden, tree):
    node_result = node_golden.call({"kind": "layoutBalanced", "root": tree})
    py_result = layout_balanced(tree)
    assert py_result["nodes"] == node_result["nodes"]
    assert py_result["edges"] == node_result["edges"]
    assert py_result["w"] == node_result["w"]
    assert py_result["h"] == node_result["h"]


def test_layout_balanced_with_sides_matches_node(node_golden):
    tree = _node("root", [_leaf("a"), _leaf("b"), _leaf("c")], w=60, h=30)
    sides = {"a": "left"}
    node_result = node_golden.call({"kind": "layoutBalanced", "root": tree, "sides": sides})
    py_result = layout_balanced(tree, sides=sides)
    assert py_result["nodes"] == node_result["nodes"]


@pytest.mark.parametrize("tree", TREES, ids=lambda t: t["id"])
def test_layout_hanging_matches_node(node_golden, tree):
    node_result = node_golden.call({"kind": "layoutHanging", "root": tree})
    py_result = layout_hanging(tree)
    assert py_result["nodes"] == node_result["nodes"]
    assert py_result["edges"] == node_result["edges"]
    assert py_result["w"] == node_result["w"]
    assert py_result["h"] == node_result["h"]


def test_layout_hanging_row_first_matches_node(node_golden):
    tree = _node("root", [_node("a", [_leaf("a1")]), _leaf("b"), _node("c", [_leaf("c1"), _leaf("c2")])])
    node_result = node_golden.call({"kind": "layoutHanging", "root": tree, "rowFirst": True})
    py_result = layout_hanging(tree, row_first=True)
    assert py_result["nodes"] == node_result["nodes"]
    assert py_result["edges"] == node_result["edges"]
    assert py_result["w"] == node_result["w"]
    assert py_result["h"] == node_result["h"]


@pytest.mark.parametrize("tree", TREES, ids=lambda t: t["id"])
def test_layout_brace_matches_node(node_golden, tree):
    node_result = node_golden.call({"kind": "layoutBrace", "root": tree})
    py_result = layout_brace(tree)
    assert py_result["nodes"] == node_result["nodes"]
    assert py_result["edges"] == node_result["edges"]
    assert py_result.get("braces", []) == node_result.get("braces", [])


def test_layout_fishbone_matches_node(node_golden):
    tree = _node("root", [
        _node("c1", [_leaf("k1"), _leaf("k2")]),
        _node("c2", [_leaf("k3")]),
        _node("c3", [_leaf("k4"), _leaf("k5")]),
    ])
    node_result = node_golden.call({"kind": "layoutFishbone", "root": tree})
    py_result = layout_fishbone(tree)
    assert py_result["nodes"] == node_result["nodes"]
    assert py_result["edges"] == node_result["edges"]
    assert py_result["w"] == node_result["w"]
    assert py_result["h"] == node_result["h"]


def test_layout_timeline_map_matches_node(node_golden):
    tree = _node("root", [_node("a", [_leaf("a1")]), _node("b", [_leaf("b1")]), _node("c", [_leaf("c1")])])
    node_result = node_golden.call({"kind": "layoutTimelineMap", "root": tree})
    py_result = layout_timeline_map(tree)
    assert py_result["nodes"] == node_result["nodes"]
    assert py_result["edges"] == node_result["edges"]
    assert py_result["w"] == node_result["w"]
    assert py_result["h"] == node_result["h"]


@pytest.mark.parametrize("tree", TREES, ids=lambda t: t["id"])
@pytest.mark.parametrize("axis", ["x", "y"])
def test_mirror_matches_node(node_golden, tree, axis):
    layout = layout_tree(tree, dir="right")
    node_result = node_golden.call({"kind": "mirror", "layout": layout, "axis": axis})
    py_result = mirror(layout, axis)
    assert py_result["nodes"] == node_result["nodes"]
    assert py_result["edges"] == node_result["edges"]


def test_layout_tree_duplicate_id_raises():
    tree = _node("root", [_leaf("a"), _leaf("a")])
    with pytest.raises(ValueError):
        layout_tree(tree)
