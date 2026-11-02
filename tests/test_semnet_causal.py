"""Golden-master tests for causal_band()/layout_chart()/render_chart() against Node's
causalLoop()/layoutChart()/renderChart(), plus the standalone pieces that have their own
golden CLI cases (analyze_causal_loops, check_ring, band_inset, ring_side)."""

from __future__ import annotations

import pytest

from svg_diagram.charts import layout_chart, render_chart
from svg_diagram.semnet_analysis import analyze_causal_loops
from svg_diagram.semnet_causal import band_inset, causal_band, causal_texts, check_ring, loop_names, resolve_causal, ring_side, sign_text

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


TRIANGLE_NODES = [{"id": "a", "label": "流入"}, {"id": "b", "label": "在庫"}, {"id": "c", "label": "流出"}]
TRIANGLE_LINKS = [{"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "c", "polarity": "+"}, {"from": "c", "to": "a", "polarity": "-"}]

RING4_NODES = [{"id": "a", "label": "受注"}, {"id": "b", "label": "生産"}, {"id": "c", "label": "在庫"}, {"id": "d", "label": "配送"}]
RING4_LINKS = [{"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "c", "polarity": "+"}, {"from": "c", "to": "d", "polarity": "+"}, {"from": "d", "to": "a", "polarity": "+"}]

SELF_LOOP_NODES = [{"id": "a", "label": "在庫"}, {"id": "b", "label": "注文"}]
SELF_LOOP_LINKS = [{"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "a", "polarity": "+"}, {"from": "a", "to": "a", "polarity": "+"}]

TWO_LOOPS_NODES = [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}, {"id": "d", "label": "D"}, {"id": "e", "label": "E"}]
TWO_LOOPS_LINKS = [
    {"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "a", "polarity": "-"},
    {"from": "c", "to": "d", "polarity": "+"}, {"from": "d", "to": "e", "polarity": "+"}, {"from": "e", "to": "c", "polarity": "+"},
]

CAUSAL_CASES = [
    {"id": "layered-default", "nodes": TRIANGLE_NODES, "links": TRIANGLE_LINKS, "opts": {}, "w": 900},
    {"id": "layered-tb", "nodes": TRIANGLE_NODES, "links": TRIANGLE_LINKS, "opts": {"direction": "TB"}, "w": 500},
    {
        "id": "layered-delay-label",
        "nodes": TRIANGLE_NODES,
        "links": [{"from": "a", "to": "b", "polarity": "+", "label": "遅延あり", "delay": True}, {"from": "b", "to": "c", "polarity": "+"}, {"from": "c", "to": "a", "polarity": "-"}],
        "opts": {},
        "w": 900,
    },
    {
        "id": "layered-intervention-top",
        "nodes": TRIANGLE_NODES, "links": TRIANGLE_LINKS,
        "opts": {"interventions": [{"id": "iv1", "label": "施策1", "to": "b", "polarity": "same", "delay": True}]},
        "w": 900,
    },
    {
        "id": "layered-intervention-left-tb",
        "nodes": TRIANGLE_NODES, "links": TRIANGLE_LINKS,
        "opts": {"direction": "TB", "interventions": [{"id": "iv1", "label": "施策1", "to": ["a", "b"], "polarity": "opposite"}]},
        "w": 500,
    },
    {"id": "layered-two-loops", "nodes": TWO_LOOPS_NODES, "links": TWO_LOOPS_LINKS, "opts": {}, "w": 1000},
    {"id": "ring-simple", "nodes": RING4_NODES, "links": RING4_LINKS, "opts": {"layout": "ring"}, "w": 900},
    {"id": "ring-straighten-false", "nodes": RING4_NODES, "links": RING4_LINKS, "opts": {"layout": "ring", "straighten": False}, "w": 900},
    {"id": "ring-self-loop", "nodes": SELF_LOOP_NODES, "links": SELF_LOOP_LINKS, "opts": {"layout": "ring"}, "w": 700},
    {
        "id": "ring-interventions",
        "nodes": RING4_NODES, "links": RING4_LINKS,
        "opts": {"layout": "ring", "interventions": [{"id": "iv1", "label": "施策1", "to": "a", "polarity": "+"}, {"id": "iv2", "label": "施策2", "to": "c", "polarity": "-"}]},
        "w": 900,
    },
]


def _round_segs(segs: list[dict] | None) -> list[dict] | None:
    """Ring layouts place points via 40 bisection rounds of math.cos/sin; Python's libm and
    V8's Math.cos/sin disagree in the last bit for some inputs, so `segs` (raw, unrounded
    internal collision-check data — never rendered; `items`/`boxes` round through js_round
    and always match exactly) is compared to 9 decimals rather than bit-for-bit."""
    if segs is None:
        return None
    return [{k: round(v, 9) for k, v in seg.items()} for seg in segs]


def _band(case: dict) -> dict:
    opts = case["opts"]
    return causal_band(
        case["nodes"], case["links"],
        direction=opts.get("direction"), interventions=opts.get("interventions"), layout=opts.get("layout"), straighten=opts.get("straighten"),
    )


@pytest.mark.parametrize("case", CAUSAL_CASES, ids=lambda c: c["id"])
def test_layout_causal_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutChart", "chartKind": "causal", "nodes": case["nodes"], "links": case["links"], "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]})
    py_result = layout_chart(_band(case), 0, 0, case["w"], _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "kind", "size", "alt", "items", "boxes", "solids", "anchors", "omitted", "edges"):
        assert py_result.get(key) == node_result.get(key), key
    assert _round_segs(py_result.get("segs")) == _round_segs(node_result.get("segs")), "segs"


@pytest.mark.parametrize("case", CAUSAL_CASES, ids=lambda c: c["id"])
def test_render_causal_matches_node(node_golden, case):
    laid = layout_chart(_band(case), 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderChart", "band": laid})
    py_result = render_chart(laid)
    assert py_result == node_result


ANALYZE_CASES = [
    {"id": "triangle-mixed", "nodes": ["a", "b", "c"], "links": TRIANGLE_LINKS},
    {"id": "ring4", "nodes": ["a", "b", "c", "d"], "links": RING4_LINKS},
    {"id": "self-loop-plus-loop", "nodes": ["a", "b"], "links": SELF_LOOP_LINKS},
    {"id": "two-independent-loops", "nodes": ["a", "b", "c", "d", "e"], "links": TWO_LOOPS_LINKS},
    {"id": "no-cycle", "nodes": ["a", "b", "c"], "links": [{"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "c", "polarity": "+"}]},
]


@pytest.mark.parametrize("case", ANALYZE_CASES, ids=lambda c: c["id"])
def test_analyze_causal_loops_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "analyzeCausalLoops", "nodes": case["nodes"], "links": case["links"]})
    py_result = analyze_causal_loops(case["nodes"], case["links"])
    assert py_result == node_result


def test_analyze_causal_loops_rejects_duplicate_node_id():
    with pytest.raises(ValueError):
        analyze_causal_loops(["a", "a"], [])


def test_analyze_causal_loops_rejects_unknown_link_node():
    with pytest.raises(ValueError):
        analyze_causal_loops(["a", "b"], [{"from": "a", "to": "nope", "polarity": "+"}])


def test_analyze_causal_loops_rejects_invalid_polarity():
    with pytest.raises(ValueError):
        analyze_causal_loops(["a", "b"], [{"from": "a", "to": "b", "polarity": "weird"}])


def _loops_of(nodes: list[str], links: list[dict]) -> list[dict]:
    return analyze_causal_loops(nodes, links)


CHECK_RING_OK_CASES = [
    {"id": "ring4", "node_dicts": RING4_NODES, "links": RING4_LINKS},
    {"id": "self-loop-plus-loop", "node_dicts": SELF_LOOP_NODES, "links": SELF_LOOP_LINKS},
]


@pytest.mark.parametrize("case", CHECK_RING_OK_CASES, ids=lambda c: c["id"])
def test_check_ring_passes_matches_node(node_golden, case):
    ids = [n["id"] for n in case["node_dicts"]]
    loops = _loops_of(ids, case["links"])
    node_result = node_golden.call({"kind": "checkRing", "nodes": case["node_dicts"], "links": case["links"], "loops": loops})
    assert node_result is None
    assert check_ring(case["node_dicts"], case["links"], loops, None) is None


def test_check_ring_rejects_direction():
    loops = _loops_of(["a", "b", "c", "d"], RING4_LINKS)
    with pytest.raises(ValueError):
        check_ring(RING4_NODES, RING4_LINKS, loops, "LR")


def test_check_ring_rejects_no_loop():
    nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    links = [{"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "c", "polarity": "+"}]
    loops = _loops_of(["a", "b", "c"], links)
    with pytest.raises(ValueError):
        check_ring(nodes, links, loops, None)


def test_check_ring_rejects_two_loops():
    loops = _loops_of(["a", "b", "c", "d", "e"], TWO_LOOPS_LINKS)
    with pytest.raises(ValueError):
        check_ring(TWO_LOOPS_NODES, TWO_LOOPS_LINKS, loops, None)


def test_check_ring_rejects_node_outside_loop():
    nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]
    links = [{"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "a", "polarity": "+"}]
    loops = _loops_of(["a", "b", "c", "d"], links)
    with pytest.raises(ValueError):
        check_ring(nodes, links, loops, None)


def test_check_ring_rejects_loop_too_small():
    nodes = [{"id": "a"}]
    links = [{"from": "a", "to": "a", "polarity": "+"}]
    loops = _loops_of(["a"], links)
    with pytest.raises(ValueError):
        check_ring(nodes, links, loops, None)


def test_check_ring_rejects_loop_too_big():
    ids = [chr(ord("a") + i) for i in range(9)]
    nodes = [{"id": i} for i in ids]
    links = [{"from": ids[i], "to": ids[(i + 1) % 9], "polarity": "+"} for i in range(9)]
    loops = _loops_of(ids, links)
    with pytest.raises(ValueError):
        check_ring(nodes, links, loops, None)


def test_check_ring_rejects_chord():
    nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    links = [{"from": "a", "to": "b", "polarity": "+"}, {"from": "b", "to": "c", "polarity": "+"}, {"from": "c", "to": "a", "polarity": "+"}, {"from": "a", "to": "c", "polarity": "-"}]
    loops = _loops_of(["a", "b", "c"], links)
    with pytest.raises(ValueError):
        check_ring(nodes, links, loops, None)


BAND_INSET_CASES = [
    {"id": "left", "side": "left", "items": [{"id": "x", "label": "L", "to": ["a"], "w": 80}], "attempt": 0},
    {"id": "left-two-items-attempt2", "side": "left", "items": [{"id": "x", "label": "L", "to": ["a"], "w": 80}, {"id": "y", "label": "LL", "to": ["b"], "w": 140}], "attempt": 2},
    {"id": "top", "side": "top", "items": [{"id": "x", "label": "L", "to": ["a"], "w": 80}], "attempt": 0},
    {"id": "top-attempt3", "side": "top", "items": [{"id": "x", "label": "L", "to": ["a"], "w": 80}], "attempt": 3},
]


@pytest.mark.parametrize("case", BAND_INSET_CASES, ids=lambda c: c["id"])
def test_band_inset_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "bandInset", "side": case["side"], "items": case["items"], "attempt": case["attempt"]})
    py_result = band_inset(case["side"], case["items"], case["attempt"])
    assert py_result == node_result


RING_SIDE_CASES = [
    {"id": "n4-top", "loopNodes": ["a", "b", "c", "d"], "to": ["a"]},
    {"id": "n4-bottom", "loopNodes": ["a", "b", "c", "d"], "to": ["c"]},
    {"id": "n4-boundary-upper", "loopNodes": ["a", "b", "c", "d"], "to": ["b"]},
    {"id": "n4-boundary-upper2", "loopNodes": ["a", "b", "c", "d"], "to": ["d"]},
    {"id": "n6-tie", "loopNodes": ["a", "b", "c", "d", "e", "f"], "to": ["a", "d"]},
    {"id": "n5-multi", "loopNodes": ["a", "b", "c", "d", "e"], "to": ["a", "c", "d"]},
]


@pytest.mark.parametrize("case", RING_SIDE_CASES, ids=lambda c: c["id"])
def test_ring_side_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "ringSide", "loopNodes": case["loopNodes"], "to": case["to"]})
    py_result = ring_side(case["loopNodes"], case["to"])
    assert py_result == node_result


def test_loop_names_numbers_within_kind():
    loops = [{"kind": "B", "nodes": ["a", "b"]}, {"kind": "R", "nodes": ["c", "d", "e"]}, {"kind": "B", "nodes": ["f", "g"]}]
    assert loop_names(loops) == ["B1", "R1", "B2"]


def test_sign_text_maps_same_opposite():
    assert sign_text("same") == "+"
    assert sign_text("opposite") == "-"
    assert sign_text("+") == "+"
    assert sign_text("-") == "-"


def test_causal_texts_covers_nodes_links_loops_interventions():
    spec = resolve_causal(
        TRIANGLE_NODES,
        [{"from": "a", "to": "b", "polarity": "+", "label": "L", "delay": True}, {"from": "b", "to": "c", "polarity": "+"}, {"from": "c", "to": "a", "polarity": "-"}],
        interventions=[{"id": "iv1", "label": "施策1", "to": "b", "polarity": "opposite", "delay": True}],
    )
    texts = causal_texts(spec)
    assert ("流入", 700) in texts
    assert ("+", 700) in texts
    assert ("-", 700) in texts
    assert ("||", 700) in texts
    assert ("L", 400) in texts
    assert ("B1", 700) in texts
    assert ("施策1", 700) in texts


def test_causal_rejects_empty_nodes():
    with pytest.raises(ValueError):
        causal_band([], [])


def test_causal_rejects_invalid_layout():
    with pytest.raises(ValueError):
        causal_band(TRIANGLE_NODES, TRIANGLE_LINKS, layout="diagonal")


def test_causal_rejects_ring_with_direction():
    with pytest.raises(ValueError):
        causal_band(RING4_NODES, RING4_LINKS, layout="ring", direction="LR")


def test_causal_intervention_rejects_unknown_target():
    with pytest.raises(ValueError):
        causal_band(TRIANGLE_NODES, TRIANGLE_LINKS, interventions=[{"id": "iv1", "label": "L", "to": "nope", "polarity": "+"}])


def test_causal_intervention_rejects_targeting_another_intervention():
    with pytest.raises(ValueError):
        causal_band(
            TRIANGLE_NODES, TRIANGLE_LINKS,
            interventions=[{"id": "iv1", "label": "L1", "to": "b", "polarity": "+"}, {"id": "iv2", "label": "L2", "to": "iv1", "polarity": "+"}],
        )


def test_causal_intervention_rejects_duplicate_target():
    with pytest.raises(ValueError):
        causal_band(TRIANGLE_NODES, TRIANGLE_LINKS, interventions=[{"id": "iv1", "label": "L", "to": ["b", "b"], "polarity": "+"}])


def test_causal_intervention_rejects_invalid_polarity():
    with pytest.raises(ValueError):
        causal_band(TRIANGLE_NODES, TRIANGLE_LINKS, interventions=[{"id": "iv1", "label": "L", "to": "b", "polarity": "weird"}])


def test_causal_intervention_rejects_non_bool_delay():
    with pytest.raises(ValueError):
        causal_band(TRIANGLE_NODES, TRIANGLE_LINKS, interventions=[{"id": "iv1", "label": "L", "to": "b", "polarity": "+", "delay": "yes"}])


def test_causal_intervention_rejects_empty_to():
    with pytest.raises(ValueError):
        causal_band(TRIANGLE_NODES, TRIANGLE_LINKS, interventions=[{"id": "iv1", "label": "L", "to": [], "polarity": "+"}])


def test_causal_intervention_rejects_id_collision_with_node():
    with pytest.raises(ValueError):
        causal_band(TRIANGLE_NODES, TRIANGLE_LINKS, interventions=[{"id": "a", "label": "L", "to": "b", "polarity": "+"}])


def test_causal_rejects_unknown_link_node():
    with pytest.raises(ValueError):
        causal_band(TRIANGLE_NODES, [{"from": "a", "to": "nope", "polarity": "+"}])


def test_causal_rejects_invalid_link_polarity():
    with pytest.raises(ValueError):
        causal_band(TRIANGLE_NODES, [{"from": "a", "to": "b", "polarity": "weird"}])
