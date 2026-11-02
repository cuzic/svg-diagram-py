"""Golden-master tests for layout_flow_shape()/render_flow_shape() against Node's
layoutFlowShape()/renderFlowShape() (both exported — live-tested via the shared dummy
width function). Covers all 7 flow-shape kinds: chevron/funnel/cycle/venn/concentric/
emblem/valueChain."""

import pytest

from svg_diagram.flow_shapes import (
    chevron_band,
    concentric_band,
    cycle_band,
    emblem_band,
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


EMBLEM_CASES = [
    {"items": [{"label": "課題"}], "opts": {}},
    {"items": [{"label": "課題", "sub": "3 件"}, {"label": "原因"}], "opts": {}},
    {
        "items": [
            {"label": "円", "shape": "circle"}, {"label": "角", "shape": "square"}, {"label": "三角", "shape": "triangle"},
            {"label": "菱形", "shape": "diamond"}, {"label": "六角", "shape": "hexagon"}, {"label": "台形", "shape": "trapezoid"},
            {"label": "逆台形", "shape": "inverted-trapezoid"}, {"label": "平行四辺形", "shape": "parallelogram"}, {"label": "矢印", "shape": "pentagon-down"},
            {"label": "錠剤", "shape": "pill"}, {"label": "角丸", "shape": "rounded"}, {"label": "文書", "shape": "document"}, {"label": "円柱", "shape": "cylinder"},
        ],
        "opts": {},
    },
    {"items": [{"label": "重要", "shape": "triangle", "tone": "danger", "id": "warn"}], "opts": {}},
    {"items": [{"label": "A", "sub": "補足テキストが長い場合の折返し確認用"}, {"label": "B"}], "opts": {"shape": "rounded", "gap": 24}},
    {"items": [{"label": f"項目{i}"} for i in range(7)], "opts": {"minSize": 80}},
    {"items": [{"label": "ア"}, {"label": "イ", "tone": "accent"}, {"label": "ウ", "tone": "muted"}], "opts": {"shape": "document"}},
]


@pytest.mark.parametrize("case", EMBLEM_CASES, ids=lambda c: str(c))
def test_emblem_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutFlowShape", "shape": "emblem", "x": 0, "y": 0, "cw": 600, **case})
    opts = case["opts"]
    band = emblem_band(case["items"], shape=opts.get("shape"), gap=opts.get("gap"), min_size=opts.get("minSize"))
    py_result = layout_flow_shape(band, 0, 0, 600, _width_of, ROLES, "phrase")
    for key in ("x", "y", "w", "h", "primitives", "texts", "anchors", "labelBoxes", "bounds"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", EMBLEM_CASES, ids=lambda c: str(c))
def test_render_emblem_matches_node(node_golden, case):
    opts = case["opts"]
    band = emblem_band(case["items"], shape=opts.get("shape"), gap=opts.get("gap"), min_size=opts.get("minSize"))
    laid = layout_flow_shape(band, 0, 0, 600, _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderFlowShape", "band": laid})
    py_result = render_flow_shape(laid)
    assert py_result == node_result


def test_emblem_rejects_unknown_shape():
    with pytest.raises(ValueError):
        emblem_band([{"label": "a"}], shape="nope")


def test_emblem_rejects_negative_gap():
    with pytest.raises(ValueError):
        emblem_band([{"label": "a"}], gap=-1)


def test_emblem_rejects_min_size_out_of_range():
    with pytest.raises(ValueError):
        emblem_band([{"label": "a"}], min_size=10)


def test_emblem_rejects_min_size_wider_than_band():
    band = emblem_band([{"label": "a"}], min_size=320)
    with pytest.raises(ValueError):
        layout_flow_shape(band, 0, 0, 200, _width_of, ROLES, "phrase")


def test_emblem_rejects_label_too_long_for_any_size():
    band = emblem_band([{"label": "あ" * 300}])
    with pytest.raises(ValueError):
        layout_flow_shape(band, 0, 0, 200, _width_of, ROLES, "phrase")


def test_cycle_rejects_bad_step_count():
    with pytest.raises(ValueError):
        cycle_band([{"label": "a"}, {"label": "b"}])
