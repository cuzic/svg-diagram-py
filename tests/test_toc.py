"""Golden-master tests for cause_band()/layout_cause_band()/layout_cause_band_once()/
render_cause() against Node's causeTree()/layoutCauseBand()/layoutCauseBandOnce()/
renderCause(), reusing the exact topologies Node's own test/toc-fit.test.ts and
test/cause-hop.test.ts use to exercise the order search (ADR 0019 D4), the AND-crossing/
side-by-side/aside passes (ADR 0016 D11-D14) and the hop-over crossings (ADR 0028) — a
different width function (`_width_of`, matching this port's `peopleWidthOf` convention, not
those files' own `fixedW`) is used throughout, so this is a pure topology/structure reuse,
not a byte-for-byte replay of their assertions."""

from __future__ import annotations

import pytest

from svg_diagram.cause_clash import and_clashes
from svg_diagram.toc import cause_band, layout_cause_band, layout_cause_band_once, render_cause
from svg_diagram.toc_analysis import core_drivers, reach_counts

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}
ENV = {"wrap": "phrase", "keepWords": False, "space": 1}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


def _n(node_id: str, **extra) -> dict:
    return {"id": node_id, "label": node_id, **extra}


_OPT_KEYS = {
    "dir": "dir", "maxNodeW": "max_node_w", "coreDriver": "core_driver", "roleTags": "role_tags", "hop": "hop",
    "tree": "tree", "layer": "layer", "counts": "counts", "coreDriverLabel": "core_driver_label", "returns": "returns",
    "straighten": "straighten", "fold": "fold", "alt": "alt", "id": "id", "reveal": "reveal", "until": "until", "base": "base",
}


def _band(nodes, links, opts: dict | None = None) -> dict:
    opts = opts or {}
    return cause_band(nodes, links, **{_OPT_KEYS[k]: v for k, v in opts.items()})


def _layout_once(nodes, links, opts=None, w=1400, env=None):
    return layout_cause_band_once(_band(nodes, links, opts), 0, 0, w, _width_of, ROLES, env or ENV)


def _layout(nodes, links, opts=None, w=1400, env=None):
    return layout_cause_band(_band(nodes, links, opts), 0, 0, w, _width_of, ROLES, env or ENV)


def _and_crossings(t: dict) -> int:
    return sum(1 for c in and_clashes(t["edges"], t["ands"]) if c["how"] == "crosses")


# ADR 0019 D4: the arrows into an effect with an AND cross; another written order is tried and kept only when it is strictly better
NINE_LINKS = [
    {"from": "n0", "to": "n2"}, {"from": ["n0", "n1"], "to": "n3"}, {"from": "n1", "to": "n4"}, {"from": "n0", "to": "n4"},
    {"from": "n2", "to": "n5"}, {"from": "n3", "to": "n5"}, {"from": "n0", "to": "n6"}, {"from": "n0", "to": "n7"},
    {"from": "n6", "to": "n7"}, {"from": "n1", "to": "n7"}, {"from": "n1", "to": "n8"},
]
NINE_NODES = [_n(f"n{i}") for i in range(9)]

# ADR 0016 D11: the long arrow into an AND and the direct one that shared a lane
D11_NODES = [_n(f"n{i}") for i in range(12)]
D11_LINKS = [
    {"from": ["n1", "n0"], "to": "n2"}, {"from": "n0", "to": "n3"}, {"from": "n1", "to": "n4"}, {"from": "n2", "to": "n4"},
    {"from": ["n2", "n0"], "to": "n5"}, {"from": ["n5", "n2"], "to": "n6"}, {"from": "n0", "to": "n7"}, {"from": "n5", "to": "n7"},
    {"from": "n2", "to": "n8"}, {"from": ["n2", "n7"], "to": "n9"}, {"from": "n8", "to": "n10"}, {"from": ["n5", "n3", "n10"], "to": "n11"},
]

# ADR 0016 D12: a long arrow's run through the layers beside another arrow's last run into the same AND head
D12_NODES = [_n(f"n{i}") for i in range(10)]
D12_LINKS = [
    {"from": "n0", "to": "n1"}, {"from": ["n0", "n1"], "to": "n2"}, {"from": "n0", "to": "n3"}, {"from": "n2", "to": "n4"},
    {"from": ["n0", "n2", "n4"], "to": "n5"}, {"from": "n3", "to": "n6"}, {"from": ["n4", "n0", "n1"], "to": "n7"},
    {"from": "n6", "to": "n8"}, {"from": ["n5", "n1"], "to": "n9"},
]

# ADR 0016 D13: a direct arrow's first run along the last run of another arrow into the same AND
D13_NODES = [_n(f"n{i}") for i in range(11)]
D13_LINKS = [
    {"from": "n0", "to": "n1"}, {"from": "n1", "to": "n2"}, {"from": ["n0", "n1"], "to": "n3"}, {"from": ["n2", "n3"], "to": "n4"},
    {"from": "n3", "to": "n5"}, {"from": "n1", "to": "n6"}, {"from": "n6", "to": "n7"}, {"from": "n3", "to": "n8"},
    {"from": ["n8", "n0"], "to": "n9"}, {"from": "n0", "to": "n10"},
]

# ADR 0019 D4 widened: the search is entered by any crossing, not only an AND's
NOAND_NODES = [_n(f"n{i}") for i in range(8)]
NOAND_LINKS = [
    {"from": "n0", "to": "n1"}, {"from": "n1", "to": "n2"}, {"from": "n1", "to": "n3"}, {"from": "n0", "to": "n4"},
    {"from": "n4", "to": "n5"}, {"from": "n1", "to": "n6"}, {"from": "n2", "to": "n7"}, {"from": "n1", "to": "n7"},
]

# a 7-node loop with a declared return (`back: true`), for hop true/false/default parity
LOOP7_NODES = [_n(c) for c in "abcdefg"]
LOOP7_LINKS = [
    {"from": "a", "to": "b"}, {"from": "b", "to": "c"}, {"from": "b", "to": "d"}, {"from": "c", "to": "e"},
    {"from": "d", "to": "f"}, {"from": "e", "to": "g"}, {"from": "f", "to": "g"}, {"from": "g", "to": "a", "back": True},
]

# test/cause-hop.test.ts's FRT fixture: ordinary arrows cross (no return at all)
FRT_IDS = ["inj1", "inj2", "inj3", "pre1", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "de1", "de2", "de3"]
FRT_NODES = [_n(i) for i in FRT_IDS]
FRT_LINKS = [
    {"from": ["inj1", "pre1"], "to": "n1"}, {"from": "n1", "to": "n2"}, {"from": "inj2", "to": "n3"}, {"from": "inj2", "to": "n5"},
    {"from": "n3", "to": "n4"}, {"from": "inj3", "to": "n6"}, {"from": ["n6", "n5"], "to": "n7"}, {"from": "n2", "to": "de1"},
    {"from": "n4", "to": "de1"}, {"from": "n7", "to": "de1"}, {"from": "n3", "to": "de1"}, {"from": ["n2", "n4"], "to": "de2"},
    {"from": "n7", "to": "de2"}, {"from": "n6", "to": "de3"},
]

# diagram({density: 'compact'})
DENSITY_NODES = [_n(i) for i in ["u1", "u2", "a1", "a2", "a3", "b1", "b2"]]
DENSITY_LINKS = [
    {"from": "b1", "to": "a1"}, {"from": "b2", "to": "a2"}, {"from": "a1", "to": "u1"}, {"from": "a2", "to": "u1"},
    {"from": ["a1", "a2"], "to": "a3"}, {"from": "a3", "to": "u2"},
]


LAYOUT_CASES = [
    {"id": "and-crossing-search", "nodes": NINE_NODES, "links": NINE_LINKS, "opts": {"tree": "frt"}},
    {"id": "no-and-crossing-fine", "nodes": [_n("a"), _n("b"), _n("c")], "links": [{"from": ["a", "b"], "to": "c"}], "opts": {}},
    {"id": "d11-lane-sharing", "nodes": D11_NODES, "links": D11_LINKS, "opts": {"tree": "frt", "dir": "up"}, "w": 1800},
    {"id": "d12-aside", "nodes": D12_NODES, "links": D12_LINKS, "opts": {"tree": "frt", "dir": "up"}, "w": 1800},
    {"id": "d13-turn-beside", "nodes": D13_NODES, "links": D13_LINKS, "opts": {"tree": "frt", "dir": "up"}, "w": 1800},
    {"id": "no-and-crossings-only", "nodes": NOAND_NODES, "links": NOAND_LINKS, "opts": {"tree": "frt", "dir": "up", "straighten": False}, "w": 1800},
    {"id": "loop-no-hop", "nodes": LOOP7_NODES, "links": LOOP7_LINKS, "opts": {"dir": "up"}, "w": 1800},
    {"id": "loop-hop-true", "nodes": LOOP7_NODES, "links": LOOP7_LINKS, "opts": {"dir": "up", "hop": True}, "w": 1800},
    {"id": "frt-hop-default", "nodes": FRT_NODES, "links": FRT_LINKS, "opts": {"tree": "frt", "dir": "right"}, "w": 1800},
    {"id": "frt-hop-true", "nodes": FRT_NODES, "links": FRT_LINKS, "opts": {"tree": "frt", "dir": "right", "hop": True}, "w": 1800},
    {"id": "frt-hop-all", "nodes": FRT_NODES, "links": FRT_LINKS, "opts": {"tree": "frt", "dir": "right", "hop": "all"}, "w": 1800},
    {"id": "core-driver-and", "nodes": [_n("a", role="ude"), _n("b"), _n("c"), _n("d", role="root")], "links": [{"from": ["b", "c"], "to": "a"}, {"from": "d", "to": "b"}, {"from": "d", "to": "c"}], "opts": {"coreDriver": True}, "w": 900},
    {"id": "role-tags", "nodes": [_n("a", role="root"), _n("b", role="goal")], "links": [{"from": "a", "to": "b"}], "opts": {"roleTags": True}, "w": 900},
    {"id": "fold-true", "nodes": D11_NODES, "links": D11_LINKS, "opts": {"tree": "frt", "dir": "up", "fold": True}, "w": 1800},
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_layout_cause_band_matches_node(node_golden, case):
    w = case.get("w", 1400)
    node_result = node_golden.call({"kind": "layoutCauseBand", "nodes": case["nodes"], "links": case["links"], "opts": case["opts"], "x": 0, "y": 0, "w": w})
    py_result = _layout(case["nodes"], case["links"], case["opts"], w)
    assert py_result == node_result


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_layout_cause_band_once_matches_node(node_golden, case):
    w = case.get("w", 1400)
    node_result = node_golden.call({"kind": "layoutCauseBandOnce", "nodes": case["nodes"], "links": case["links"], "opts": case["opts"], "x": 0, "y": 0, "w": w})
    py_result = _layout_once(case["nodes"], case["links"], case["opts"], w)
    assert py_result == node_result


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["id"])
def test_render_cause_matches_node(node_golden, case):
    w = case.get("w", 1400)
    laid = _layout(case["nodes"], case["links"], case["opts"], w)
    node_result = node_golden.call({"kind": "renderCause", "band": laid})
    py_result = render_cause(laid, 1)
    assert py_result == node_result


def test_density_compact_matches_node(node_golden):
    env = {"wrap": "phrase", "keepWords": False, "space": 0.75}
    band = _band(DENSITY_NODES, DENSITY_LINKS, {"tree": "crt"})
    node_result = node_golden.call({"kind": "layoutCauseBand", "nodes": DENSITY_NODES, "links": DENSITY_LINKS, "opts": {"tree": "crt"}, "x": 0, "y": 0, "w": 940, "space": 0.75})
    py_result = layout_cause_band(band, 0, 0, 940, _width_of, ROLES, env)
    assert py_result == node_result


def test_order_search_removes_and_crossing():
    once = _layout_once(NINE_NODES, NINE_LINKS, {"tree": "frt"})
    now = _layout(NINE_NODES, NINE_LINKS, {"tree": "frt"})
    assert _and_crossings(once) >= 1, "the written order leaves a crossing"
    assert _and_crossings(now) == 0, "the search removes it"
    assert now["loose"] == []
    assert now["h"] <= once["h"] + 0.5


def test_order_search_is_deterministic():
    a = _layout(NINE_NODES, NINE_LINKS, {"tree": "frt"})
    b = _layout(NINE_NODES, NINE_LINKS, {"tree": "frt"})
    assert a == b


def test_d11_no_side_by_side_and_arrows():
    t = _layout(D11_NODES, D11_LINKS, {"tree": "frt", "dir": "up"}, w=1800)
    assert [c for c in and_clashes(t["edges"], t["ands"]) if c["how"] != "crosses"] == []
    assert t["loose"] == []


def test_d13_no_side_by_side_and_arrows():
    t = _layout(D13_NODES, D13_LINKS, {"tree": "frt", "dir": "up"}, w=1800)
    assert and_clashes(t["edges"], t["ands"]) == []
    assert t["loose"] == []


def test_hop_true_adds_reversed_key_without_moving_routes():
    plain = _layout(LOOP7_NODES, LOOP7_LINKS, {"dir": "up"}, w=1800)
    hop = _layout(LOOP7_NODES, LOOP7_LINKS, {"dir": "up", "hop": True}, w=1800)
    assert "crossings" not in plain
    assert not any("reversed" in e for e in plain["edges"])
    assert any(e.get("reversed") for e in hop["edges"])
    assert [e["points"] for e in hop["edges"]] == [e["points"] for e in plain["edges"]]
    assert hop["nodes"] == plain["nodes"]


def test_tree_defaults_hop_to_all_unless_overridden():
    assert cause_band([_n("a")], [], tree="crt").get("hop") == "all"
    assert cause_band([_n("a")], [], tree="crt", hop=False).get("hop") is False
    assert cause_band([_n("a")], [], tree="crt", hop=True).get("hop") is True
    assert cause_band([_n("a")], [], hop=None).get("hop") is None


def test_hop_all_gives_ordinary_arrow_crossings_a_hop():
    off = _layout(FRT_NODES, FRT_LINKS, {"tree": "frt", "dir": "right"}, w=1800)
    ret = _layout(FRT_NODES, FRT_LINKS, {"tree": "frt", "dir": "right", "hop": True}, w=1800)
    allh = _layout(FRT_NODES, FRT_LINKS, {"tree": "frt", "dir": "right", "hop": "all"}, w=1800)
    assert "crossings" not in ret
    assert [e["points"] for e in allh["edges"]] == [e["points"] for e in off["edges"]]
    hops = [c for c in allh.get("crossings", []) if not c.get("skipped")]
    assert len(hops) >= 1
    assert all(not allh["edges"][c["over"]].get("reversed") for c in hops)


def test_reach_counts_and_core_drivers():
    nodes = [{"id": "a", "role": "ude"}, {"id": "b"}, {"id": "c"}]
    links = [{"from": "b", "to": "a"}, {"from": "c", "to": "b"}]
    assert reach_counts(nodes, links) == {"c": 1}
    assert core_drivers({"a": 3, "b": 1, "c": 3}) == ["a", "c"]
    assert core_drivers({"a": 1}) == []


def test_cause_band_rejects_empty_nodes():
    with pytest.raises(ValueError):
        cause_band([], [])


def test_layout_rejects_duplicate_node_id():
    with pytest.raises(ValueError):
        _layout_once([_n("a"), _n("a")], [])


def test_layout_rejects_unknown_link_target():
    with pytest.raises(ValueError):
        _layout_once([_n("a")], [{"from": "a", "to": "nope"}])


def test_layout_rejects_unknown_link_cause():
    with pytest.raises(ValueError):
        _layout_once([_n("a"), _n("b")], [{"from": "nope", "to": "b"}])


def test_layout_rejects_self_cause():
    with pytest.raises(ValueError):
        _layout_once([_n("a")], [{"from": "a", "to": "a"}])


def test_layout_rejects_duplicate_link():
    with pytest.raises(ValueError):
        _layout_once([_n("a"), _n("b")], [{"from": "a", "to": "b"}, {"from": "a", "to": "b"}])


def test_cause_band_rejects_back_with_and():
    with pytest.raises(ValueError):
        cause_band([_n("a"), _n("b"), _n("c")], [{"from": ["a", "b"], "to": "c", "back": True}])


def test_cause_band_rejects_invalid_dir():
    with pytest.raises(ValueError):
        cause_band([_n("a")], [], dir="sideways")


def test_cause_band_rejects_invalid_max_node_w():
    with pytest.raises(ValueError):
        cause_band([_n("a")], [], max_node_w=10)


def test_cause_band_rejects_invalid_role():
    with pytest.raises(ValueError):
        cause_band([_n("a", role="nope")], [])


def test_cause_band_rejects_invalid_tree():
    with pytest.raises(ValueError):
        cause_band([_n("a")], [], tree="nope")


def test_cause_band_rejects_invalid_hop():
    with pytest.raises(ValueError):
        cause_band([_n("a")], [], hop="yes")


def test_cause_band_rejects_blocks_link_with_and():
    with pytest.raises(ValueError):
        cause_band([_n("a"), _n("b"), _n("c")], [{"from": ["a", "b"], "to": "c", "kind": "blocks"}])


def test_cause_band_rejects_foldsinto_on_non_trim():
    with pytest.raises(ValueError):
        cause_band([_n("a", foldsInto="x")], [])
