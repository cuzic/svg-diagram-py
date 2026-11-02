"""Golden-master tests for layout_flow_shape()/render_flow_shape() against Node's
layoutFlowShape()/renderFlowShape() (both exported — live-tested via the shared dummy
width function). chevron/funnel/cycle/venn/concentric/valueChain only — emblem is not
ported, see flow_shapes.py's module docstring."""

import pytest

from svg_diagram.flow_shapes import (
    chevron_band,
    concentric_band,
    cycle_band,
    funnel_band,
    layout_flow_shape,
    render_flow_shape,
    value_chain_band,
    venn_band,
)

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


CHEVRON_CASES = [
    {"items": [{"label": "計画"}, {"label": "実行"}, {"label": "確認"}], "opts": {}},
    {"items": [{"label": "計画"}, {"label": "実行"}, {"label": "確認"}], "opts": {"current": 1}},
    {"items": [{"label": "計画", "sub": "補足"}, {"label": "実行"}], "opts": {"direction": "vertical"}},
    {"items": [{"label": "A"}, {"label": "B"}, {"label": "C"}], "opts": {"first": "chevron", "gap": 8}},
]


@pytest.mark.parametrize("case", CHEVRON_CASES, ids=lambda c: str(c))
def test_chevron_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutFlowShape", "shape": "chevron", "x": 0, "y": 0, "cw": 600, **case})
    opts = case["opts"]
    band = chevron_band(case["items"], current=opts.get("current"), direction=opts.get("direction"), first=opts.get("first"), gap=opts.get("gap"))
    py_result = layout_flow_shape(band, 0, 0, 600, _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "primitives", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key


FUNNEL_CASES = [
    {"items": [{"label": "訪問"}, {"label": "登録"}, {"label": "購入"}], "opts": {}},
    {"items": [{"label": "訪問", "value": 1000}, {"label": "登録", "value": 300}, {"label": "購入", "value": 50}], "opts": {"scale": "value", "showRate": True}},
]


@pytest.mark.parametrize("case", FUNNEL_CASES, ids=lambda c: str(c))
def test_funnel_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutFlowShape", "shape": "funnel", "x": 0, "y": 0, "cw": 600, **case})
    opts = case["opts"]
    band = funnel_band(case["items"], scale=opts.get("scale"), show_rate=opts.get("showRate", False))
    py_result = layout_flow_shape(band, 0, 0, 600, _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "primitives", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key


CYCLE_CASES = [
    {"items": [{"label": "計画"}, {"label": "実行"}, {"label": "評価"}, {"label": "改善"}], "opts": {}},
    {"items": [{"label": "A"}, {"label": "B"}, {"label": "C"}], "opts": {"direction": "ccw", "centre": "PDCA"}},
]


@pytest.mark.parametrize("case", CYCLE_CASES, ids=lambda c: str(c))
def test_cycle_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutFlowShape", "shape": "cycle", "x": 0, "y": 0, "cw": 600, **case})
    opts = case["opts"]
    band = cycle_band(case["items"], direction=opts.get("direction"), centre=opts.get("centre"))
    py_result = layout_flow_shape(band, 0, 0, 600, _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "primitives", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key


VENN_CASES = [
    {"items": [{"name": "A"}, {"name": "B"}], "opts": {}},
    {"items": [{"name": "A"}, {"name": "B"}, {"name": "C"}], "opts": {"overlaps": [{"sets": ["A", "B"], "label": "AB"}], "centre": "全体"}},
    {"items": [{"name": "A"}, {"name": "B"}], "opts": {"universe": "宇宙"}},
]


@pytest.mark.parametrize("case", VENN_CASES, ids=lambda c: str(c))
def test_venn_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutFlowShape", "shape": "venn", "x": 0, "y": 0, "cw": 600, **case})
    opts = case["opts"]
    band = venn_band(case["items"], overlaps=opts.get("overlaps"), centre=opts.get("centre"), universe=opts.get("universe"))
    py_result = layout_flow_shape(band, 0, 0, 600, _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "primitives", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key


CONCENTRIC_CASES = [
    {"items": [{"label": "コア"}, {"label": "周辺"}], "opts": {}},
    {"items": [{"label": "コア"}, {"label": "周辺"}, {"label": "外縁"}], "opts": {"labels": "side", "order": "inner-first"}},
]


@pytest.mark.parametrize("case", CONCENTRIC_CASES, ids=lambda c: str(c))
def test_concentric_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutFlowShape", "shape": "concentric", "x": 0, "y": 0, "cw": 600, **case})
    opts = case["opts"]
    band = concentric_band(case["items"], order=opts.get("order"), labels=opts.get("labels"))
    py_result = layout_flow_shape(band, 0, 0, 600, _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "primitives", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key


VALUE_CHAIN_CASES = [
    {"items": {"primary": [{"label": "調達"}, {"label": "製造"}, {"label": "出荷"}]}, "opts": {}},
    {"items": {"support": [{"label": "人事"}], "primary": [{"label": "調達"}, {"label": "製造"}]}, "opts": {"margin": False}},
]


@pytest.mark.parametrize("case", VALUE_CHAIN_CASES, ids=lambda c: str(c))
def test_value_chain_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutFlowShape", "shape": "valueChain", "x": 0, "y": 0, "cw": 600, "items": case["items"], "opts": case["opts"]})
    opts = case["opts"]
    band = value_chain_band(support=case["items"].get("support"), primary=case["items"]["primary"], margin=opts.get("margin"))
    py_result = layout_flow_shape(band, 0, 0, 600, _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "primitives", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key


def test_render_flow_shape_matches_node(node_golden):
    band = chevron_band([{"label": "計画"}, {"label": "実行"}, {"label": "確認"}])
    laid = layout_flow_shape(band, 0, 0, 600, _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderFlowShape", "band": laid})
    py_result = render_flow_shape(laid)
    assert py_result == node_result


def test_cycle_rejects_bad_step_count():
    with pytest.raises(ValueError):
        cycle_band([{"label": "a"}, {"label": "b"}])
