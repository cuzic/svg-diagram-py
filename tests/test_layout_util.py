"""Golden-master tests for the row()/grid() width-distribution arithmetic against Node's
lib/layout-util.ts. This is pure arithmetic (no text metrics), so unlike cloud()/mindmap()/
cause() this is byte-identical to Node, not an approximation."""

import pytest

from svg_diagram.layout_util import col_slots, grid_child_geometry, grid_columns, row_child_geometry

GRID_COLUMNS_CASES = [
    {"contentWidth": 900, "n": 2, "gap": 16},
    {"contentWidth": 900, "n": 3, "gap": 16},
    {"contentWidth": 900, "n": 4, "gap": 16},
    {"contentWidth": 900, "n": 5, "gap": 16},
    {"contentWidth": 901, "n": 3, "gap": 16},
    {"contentWidth": 1000, "n": 7, "gap": 10},
    {"contentWidth": 500, "n": 2, "gap": 20, "fixedGap": True},
    {"contentWidth": 500, "n": 12, "gap": 20, "centerGutter": True},
    {"contentWidth": 500, "n": 12, "gap": 20, "centerGutter": True, "anyGap": True},
    {"contentWidth": 10, "n": 5, "gap": 16},  # too small -> null
    {"contentWidth": 300, "n": 1, "gap": 16},
    {"contentWidth": 300, "n": 6, "gap": 16, "anyGap": True},
]


@pytest.mark.parametrize("case", GRID_COLUMNS_CASES, ids=lambda c: str(c))
def test_grid_columns_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "gridColumns", **case})
    py_result = grid_columns(
        case["contentWidth"],
        case["n"],
        case["gap"],
        fixed_gap=case.get("fixedGap", False),
        center_gutter=case.get("centerGutter", False),
        any_gap=case.get("anyGap", False),
    )
    if node_result is None:
        assert py_result is None
    else:
        assert py_result == {"x": node_result["x"], "w": node_result["w"]}


ROW_CASES = [
    {"band": {"gap": 16, "children": [{"width": 160}, {"width": 160}, {"width": 160}]}, "contentWidth": 900},
    {"band": {"gap": 16, "justify": "center", "children": [{"width": 160}, {"width": 160}]}, "contentWidth": 900},
    {"band": {"gap": 16, "justify": "stretch", "children": [{}, {}, {}]}, "contentWidth": 900},
    {"band": {"gap": 16, "justify": "stretch", "children": [{"flex": 2}, {"flex": 1}, {"flex": 1}]}, "contentWidth": 901},
    {"band": {"gap": 16, "itemWidth": 200, "children": [{}, {}]}, "contentWidth": 900},
    {"band": {"cols": 12, "gap": 16, "children": [{"col": 1, "span": 6}, {"col": 7, "span": 6}]}, "contentWidth": 900},
    {"band": {"cols": 4, "gap": 16, "children": [{"span": 2}, {"span": 1}, {"span": 1}]}, "contentWidth": 900},
]


@pytest.mark.parametrize("case", ROW_CASES, ids=lambda c: str(c))
def test_row_child_geometry_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "rowChildGeometry", **case})
    py_result = row_child_geometry(case["band"], case["contentWidth"])
    assert py_result == node_result


def test_row_child_geometry_out_of_range_col_raises():
    with pytest.raises(ValueError):
        row_child_geometry({"cols": 4, "gap": 16, "children": [{"col": 3, "span": 3}]}, 900)


GRID_CASES = [
    {"band": {"cols": 3, "gap": 16}, "contentWidth": 900},
    {"band": {"cols": 5, "gap": 10}, "contentWidth": 901},
]


@pytest.mark.parametrize("case", GRID_CASES, ids=lambda c: str(c))
def test_grid_child_geometry_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "gridChildGeometry", **case})
    py_result = grid_child_geometry(case["band"], case["contentWidth"])
    assert py_result == {"xs": node_result["xs"], "ws": node_result["ws"]}


COL_SLOTS_CASES = [
    [{}, {}, {}],
    [{"span": 2}, {}, {}],
    [{"col": 3}, {}, {"span": 2}],
]


@pytest.mark.parametrize("children", COL_SLOTS_CASES, ids=lambda c: str(c))
def test_col_slots_matches_node(node_golden, children):
    node_result = node_golden.call({"kind": "colSlots", "children": children})
    py_result = col_slots(children)
    assert py_result == node_result
