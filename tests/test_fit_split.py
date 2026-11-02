"""Golden-master tests for fit_split.py's split_by_height()/split_widest() against Node's
splitByHeight()/splitWidest() (lib/fit-split.ts, both exported — live-tested via
emit_cli.ts). What to say when a layered figure fits neither the width nor the height (ADR
0019 D3); the layout itself is built via the already-ported layout_layered()."""

from __future__ import annotations

import pytest

from svg_diagram.fit_split import split_by_height, split_widest
from svg_diagram.graph_layout import layout_layered


def _n(*ids: str, w: float = 40, h: float = 20) -> list[dict]:
    return [{"id": i, "size": {"w": w, "h": h}} for i in ids]


def _e(*pairs: tuple[str, str]) -> list[dict]:
    return [{"from": a, "to": b} for a, b in pairs]


# a 4-layer chain, wide enough overall that only a mid-way cut fits a tight budget
CHAIN4 = (_n("a", "b", "c", "d"), _e(("a", "b"), ("b", "c"), ("c", "d")))
# a single layer with two nodes far apart in the across axis (the "widest layer" case)
WIDE_LAYER = (_n("a", "b", "c", w=60, h=20), _e(("a", "c"), ("b", "c")))
# a single node, no layers to split
SINGLE = (_n("a"), [])
# a layer with only one node: split_widest finds nothing worth sharing
ONE_PER_LAYER = (_n("a", "b"), _e(("a", "b")))

SPLIT_BY_HEIGHT_CASES = [
    {"id": "chain4-tight-budget", "graph": CHAIN4, "budget": 50},
    {"id": "chain4-generous-budget", "graph": CHAIN4, "budget": 500},
    {"id": "chain4-impossible-budget", "graph": CHAIN4, "budget": 15},
    {"id": "single-node-no-layers", "graph": SINGLE, "budget": 50},
]


@pytest.mark.parametrize("case", SPLIT_BY_HEIGHT_CASES, ids=lambda c: c["id"])
def test_split_by_height_matches_node(node_golden, case):
    nodes, edges = case["graph"]
    node_result = node_golden.call({"kind": "splitByHeight", "nodes": nodes, "edges": edges, "opts": {}, "budget": case["budget"]})
    lay = layout_layered(nodes, edges, {})
    assert split_by_height(lay, case["budget"]) == node_result


SPLIT_WIDEST_CASES = [
    {"id": "wide-layer", "graph": WIDE_LAYER},
    {"id": "one-per-layer", "graph": ONE_PER_LAYER},
]


@pytest.mark.parametrize("case", SPLIT_WIDEST_CASES, ids=lambda c: c["id"])
def test_split_widest_matches_node(node_golden, case):
    nodes, edges = case["graph"]
    node_result = node_golden.call({"kind": "splitWidest", "nodes": nodes, "edges": edges, "opts": {}})
    lay = layout_layered(nodes, edges, {})
    assert split_widest(lay) == node_result
