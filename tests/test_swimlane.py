"""Golden-master tests for layout_swimlane_band()/render_swimlane()/render_box() against
Node's layoutSwimlaneBand()/renderSwimlane()/renderBox() (all exported — live-tested via
the shared dummy width function, same technique as test_gantt.py)."""

import pytest

from svg_diagram.swimlane import layout_swimlane_band, render_box, render_swimlane

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LANES = [{"id": "cust", "label": "顧客"}, {"id": "front", "label": "フロント"}, {"id": "back", "label": "バックエンド", "tone": "accent"}]

CASES = [
    {
        "lanes": LANES,
        "steps": [
            {"id": "order", "lane": "cust", "col": 1, "span": 1, "title": "注文する"},
            {"id": "accept", "lane": "front", "col": 2, "span": 1, "title": "受付", "body": "内容を確認して登録する"},
            {"id": "ship", "lane": "back", "col": 3, "span": 1, "title": "発送処理", "tone": "accent"},
        ],
        "cols": 3,
        "x": 0,
        "y": 0,
        "w": 900,
    },
    {  # overlapping work in one lane (row), and a column-group header
        "lanes": LANES,
        "steps": [
            {"lane": "front", "col": 1, "span": 1, "row": 0, "title": "A"},
            {"lane": "front", "col": 1, "span": 1, "row": 1, "title": "B(もう少し長い題名)"},
            {"lane": "back", "col": 2, "span": 2, "title": "まとめて処理"},
        ],
        "cols": 3,
        "phases": [{"label": "受付フェーズ", "from": 1, "to": 1}, {"label": "処理フェーズ", "from": 2, "to": 3}],
        "cols_dummy": None,
        "x": 0,
        "y": 0,
        "w": 900,
    },
    {  # a named boundary (service-blueprint's line of interaction)
        "lanes": LANES,
        "steps": [{"lane": "cust", "col": 1, "span": 1, "title": "X"}, {"lane": "front", "col": 1, "span": 1, "title": "Y"}],
        "cols": 1,
        "boundaries": [{"after": "cust", "label": "相互作用線"}, {"after": "front"}],
        "x": 0,
        "y": 0,
        "w": 900,
    },
    {  # step badge + tag, body + lines + note
        "lanes": LANES,
        "steps": [
            {
                "id": "s1", "lane": "cust", "col": 1, "span": 1, "step": 1, "title": "手順タイトル", "body": "本文テキスト",
                "lines": ["補足行1", {"text": "補足行2", "bold": True}], "note": "注記", "tag": "完了", "tone": "danger",
            },
        ],
        "cols": 1,
        "x": 0,
        "y": 0,
        "w": 900,
    },
    {  # fit: 'shrink' with narrow columns
        "lanes": LANES,
        "steps": [{"lane": "cust", "col": i, "span": 1, "title": f"工程{i}"} for i in range(1, 7)],
        "cols": 6,
        "fit": "shrink",
        "x": 0,
        "y": 0,
        "w": 700,
    },
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c.get("boundaries") or c.get("phases") or c.get("fit") or c["steps"][0].get("title")))
def test_layout_swimlane_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutSwimlaneBand", **{k: v for k, v in case.items() if k != "cols_dummy"}})
    py_result = layout_swimlane_band(
        lanes=case["lanes"], steps=case["steps"], cols=case["cols"], x=case["x"], y=case["y"], w=case["w"],
        width_of=_width_of, roles=ROLES, phases=case.get("phases"), boundaries=case.get("boundaries"),
        label_w=case.get("labelW"), col_gap=case.get("colGap"), fit=case.get("fit"),
    )
    node_frame, py_frame = node_result["frame"], py_result["frame"]
    for key in ("x", "y", "w", "h", "labelW", "bodyX", "phaseH", "phases", "lanes", "boundaries", "narrow"):
        assert py_frame.get(key) == node_frame.get(key), key
    assert len(py_result["steps"]) == len(node_result["steps"])
    for py_step, node_step in zip(py_result["steps"], node_result["steps"]):
        for key in ("x", "y", "w", "h", "wrappedRuns", "tagBox", "titleW", "stampW"):
            assert py_step.get(key) == node_step.get(key), key


def test_render_swimlane_matches_node(node_golden):
    case = CASES[3]
    py_laid = layout_swimlane_band(lanes=case["lanes"], steps=case["steps"], cols=case["cols"], x=case["x"], y=case["y"], w=case["w"], width_of=_width_of, roles=ROLES)
    node_laid = node_golden.call({"kind": "layoutSwimlaneBand", **case})

    node_frame_svg = node_golden.call({"kind": "renderSwimlane", "band": node_laid["frame"]})
    py_frame_svg = render_swimlane(py_laid["frame"], roles=ROLES)
    assert py_frame_svg == node_frame_svg

    for py_step, node_step in zip(py_laid["steps"], node_laid["steps"]):
        node_svg = node_golden.call({"kind": "renderBox", "band": node_step})
        py_svg = render_box(py_step, roles=ROLES)
        assert py_svg == node_svg


def test_swimlane_boundaries_unknown_lane_raises():
    with pytest.raises(KeyError):
        layout_swimlane_band(lanes=LANES, steps=[{"lane": "cust", "col": 1, "span": 1, "title": "x"}], cols=1, x=0, y=0, w=900, width_of=_width_of, roles=ROLES, boundaries=[{"after": "nope"}])


def test_swimlane_too_many_columns_raises():
    with pytest.raises(ValueError):
        layout_swimlane_band(lanes=LANES, steps=[{"lane": "cust", "col": i, "span": 1, "title": "x"} for i in range(1, 30)], cols=30, x=0, y=0, w=900, width_of=_width_of, roles=ROLES)
