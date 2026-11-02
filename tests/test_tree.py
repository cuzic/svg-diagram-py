"""Golden-master tests for layout_tree_band()/render_tree() against Node's layoutTreeBand()/
renderTree() (both exported — live-tested via the shared dummy width function). Covers both
tree() and mindmap() (same band, different flags — see tree.py's module docstring)."""

import pytest

from svg_diagram.tree import layout_tree_band, render_tree

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


ORG_ROOT = {"label": "社長", "children": [{"label": "開発部", "id": "dev", "children": [{"label": "開発1課"}, {"label": "開発2課"}]}, {"label": "営業部"}]}

TREE_CASES = [
    {"root": ORG_ROOT, "x": 0, "y": 0, "w": 900},
    {"root": ORG_ROOT, "x": 0, "y": 0, "w": 900, "dir": "right"},
    {"root": {"label": "ルート", "children": [{"label": "A", "tone": "accent"}, {"label": "B", "sub": "補足"}]}, "x": 10, "y": 20, "w": 700},
    {"root": {"label": "単独"}, "x": 0, "y": 0, "w": 400},
]


@pytest.mark.parametrize("case", TREE_CASES, ids=lambda c: str(c))
def test_layout_tree_band_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutTreeBand", **case})
    py_result = layout_tree_band(case["root"], case["x"], case["y"], case["w"], _width_of, ROLES, dir_opt=case.get("dir"))
    for key in ("x", "y", "w", "h", "nodes", "edges", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key


MINDMAP_CASES = [
    {"root": {"label": "テーマ", "children": [{"label": "A"}, {"label": "B"}, {"label": "C"}, {"label": "D"}]}, "x": 0, "y": 0, "w": 900, "balanced": True},
    {"root": {"label": "テーマ", "children": [{"label": "A"}, {"label": "B"}, {"label": "C"}]}, "x": 0, "y": 0, "w": 900, "balanced": True, "layoutMode": "org"},
    {"root": {"label": "テーマ", "children": [{"label": "A"}, {"label": "B"}]}, "x": 0, "y": 0, "w": 900, "balanced": True, "layoutMode": "list"},
    {"root": {"label": "テーマ", "children": [{"label": "A", "children": [{"label": "A1"}]}, {"label": "B"}]}, "x": 0, "y": 0, "w": 900, "balanced": True, "layoutMode": "brace"},
    {"root": {"label": "テーマ", "children": [{"label": "A", "children": [{"label": "A1"}]}, {"label": "B", "children": [{"label": "B1"}]}]}, "x": 0, "y": 0, "w": 900, "balanced": True, "layoutMode": "fishbone"},
    {"root": {"label": "テーマ", "children": [{"label": "A", "children": [{"label": "A1"}]}, {"label": "B"}]}, "x": 0, "y": 0, "w": 900, "balanced": True, "layoutMode": "timeline"},
    {"root": {"label": "テーマ", "children": [{"label": "A", "id": "a"}, {"label": "B"}]}, "x": 0, "y": 0, "w": 900, "balanced": True, "sides": {"a": "left"}},
    {"root": {"label": "テーマ", "children": [{"label": "A"}, {"label": "B"}]}, "x": 0, "y": 0, "w": 900, "balanced": True, "edgesOpt": "curve"},
]


@pytest.mark.parametrize("case", MINDMAP_CASES, ids=lambda c: str(c))
def test_layout_tree_band_mindmap_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutTreeBand", **case})
    py_result = layout_tree_band(
        case["root"], case["x"], case["y"], case["w"], _width_of, ROLES,
        balanced=case.get("balanced", False), layout_mode=case.get("layoutMode"), sides=case.get("sides"), edges_opt=case.get("edgesOpt"),
    )
    for key in ("x", "y", "w", "h", "nodes", "edges", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key
    if "braces" in node_result or "braces" in py_result:
        assert py_result.get("braces") == node_result.get("braces")


def test_render_tree_matches_node(node_golden):
    laid = layout_tree_band(ORG_ROOT, 0, 0, 900, _width_of, ROLES)
    node_result = node_golden.call({"kind": "renderTree", "band": laid})
    py_result = render_tree(laid)
    assert py_result == node_result


def test_tree_duplicate_id_raises():
    root = {"label": "root", "children": [{"label": "a", "id": "x"}, {"label": "b", "id": "x"}]}
    with pytest.raises(ValueError):
        layout_tree_band(root, 0, 0, 900, _width_of, ROLES)
