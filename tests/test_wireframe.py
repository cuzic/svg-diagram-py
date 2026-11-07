"""Golden-master tests for layout_wireframe()/layout_screens()/render_prims() against
Node's layoutWireframe()/layoutScreens()/renderPrims() (all exported — live-tested via
the shared dummy width function, same technique as test_gantt.py).

Scope: wireframe-parts.ts's `state`/extension node kinds are not ported (see
wireframe.py's module docstring); the cases below stay inside the core vocabulary."""

import pytest

from svg_diagram.wireframe import layout_screens, layout_wireframe, render_prims


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


SAMPLE_SCREEN = {
    "t": "col",
    "pad": 12,
    "children": [
        {"t": "appbar", "title": "ダッシュボード", "nav": ["概要", "履歴"], "active": 0, "right": ["設定"]},
        {"t": "text", "text": "本日のまとめ", "size": "title"},
        {"t": "row", "children": [
            {"t": "stat", "value": "128", "label": "件数", "tone": "accent"},
            {"t": "stat", "value": "3", "label": "警告", "tone": "danger"},
        ]},
        {"t": "tabs", "labels": ["すべて", "未対応"], "active": 1},
        {"t": "kv", "pairs": [["状態", "正常"], ["更新", "2026-11-07"]]},
        {"t": "list", "title": "最近の項目", "items": [
            {"text": "項目1", "active": True, "badge": "NEW"},
            "項目2(かなり長めのラベルを書いてみる文章)",
        ]},
        {"t": "table", "columns": ["名前", "値"], "rows": [["A", "1"], [{"text": "B", "bold": True}, {"badge": "済"}]]},
        {"t": "alert", "text": "通信が不安定です", "tone": "danger"},
        {"t": "seek", "from": "0:00", "to": "3:45", "at": 0.6, "marks": [0.2, 0.8]},
        {"t": "input", "label": "検索"},
        {"t": "select", "label": "並び順"},
        {"t": "btn", "label": "更新する", "primary": True},
        {"t": "image", "label": "写真なし"},
    ],
}

VISUAL_SCREEN = {
    "t": "col",
    "children": [
        {"t": "chart", "kind": "bar", "points": [0.2, 0.5, 0.9], "threshold": 0.8, "thresholdLabel": "上限", "label": "負荷", "xLabels": ["月", "火"], "h": 160},
        {"t": "map", "plan": "site", "markers": [{"x": 0.3, "y": 0.4, "kind": "robot", "label": "R1"}, {"x": 0.6, "y": 0.5, "kind": "alert"}], "legend": [{"kind": "robot", "label": "ロボット"}], "h": 160},
        {"t": "heat", "probe": {"x": 0.5, "y": 0.5, "value": "38℃"}, "scale": [20, 40], "unit": "℃", "h": 160},
        {"t": "pointcloud", "h": 120},
        {"t": "video", "live": True, "label": "カメラ1", "h": 120},
    ],
}


@pytest.mark.parametrize("case", [
    {"root": SAMPLE_SCREEN, "x": 0, "y": 0, "w": 420, "title": "ホーム", "tag": "新規", "h": 900},
    {"root": VISUAL_SCREEN, "x": 0, "y": 0, "w": 500, "h": 850},
    {"root": {"t": "col", "children": [{"t": "text", "text": "スケルトン表示"}, {"t": "list", "items": ["A", "B"]}]}, "x": 0, "y": 0, "w": 300, "skeleton": True},
    {"root": {"t": "text", "text": "注記あり本文"}, "x": 0, "y": 0, "w": 400, "notes": ["最初の注記", {"title": "二つ目", "text": "本文付き"}]},
    {
        "root": {"t": "text", "text": "ダイアログの下地"}, "x": 0, "y": 0, "w": 500,
        "overlays": {"t": "dialog", "title": "確認", "body": "本当に削除しますか?", "buttons": [{"t": "btn", "label": "キャンセル"}, {"t": "btn", "label": "削除", "danger": True, "primary": True}]},
    },
    {"root": {"t": "col", "children": [{"t": "text", "text": "x", "mark": "new"}, {"t": "text", "text": "y", "mark": "changed"}]}, "x": 0, "y": 0, "w": 300},
], ids=lambda c: str(c.get("skeleton") or c.get("notes") or c.get("overlays", {}).get("t") if isinstance(c.get("overlays"), dict) else c.get("title") or "visual"))
def test_layout_wireframe_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutWireframe", **case})
    py_result = layout_wireframe({k: v for k, v in case.items() if k not in ("x", "y", "w")}, case["x"], case["y"], case["w"], _width_of, "phrase")
    for key in ("x", "y", "w", "h", "prims", "callouts", "anchors"):
        assert py_result.get(key) == node_result.get(key), key


def test_render_prims_matches_node(node_golden):
    laid = layout_wireframe({"root": SAMPLE_SCREEN, "title": "ホーム", "h": 900}, 0, 0, 420, _width_of, "phrase")
    node_svg = node_golden.call({"kind": "renderPrims", "band": laid})
    py_svg = render_prims(laid)
    assert py_svg == node_svg


def test_layout_screens_grid_matches_node(node_golden):
    case = {
        "items": [
            {"title": "画面1", "root": {"t": "text", "text": "A"}, "id": "s1"},
            {"title": "画面2", "root": {"t": "text", "text": "B"}, "h": "fit"},
            {"title": "画面3", "root": {"t": "list", "items": ["x", "y"]}},
        ],
        "cols": 2,
        "x": 0, "y": 0, "w": 700,
    }
    node_result = node_golden.call({"kind": "layoutScreens", **case})
    py_result = layout_screens({k: v for k, v in case.items() if k not in ("x", "y", "w")}, case["x"], case["y"], case["w"], _width_of, "phrase")
    for key in ("x", "y", "w", "h", "prims", "anchors"):
        assert py_result.get(key) == node_result.get(key), key


def test_layout_screens_matrix_matches_node(node_golden):
    case = {
        "matrix": {
            "cols": ["正常", "異常"],
            "rows": [
                {"label": "部品A", "note": "補足", "cells": [{"t": "text", "text": "OK"}, "na"]},
                {"label": "部品B", "cells": [{"t": "text", "text": "OK"}, None]},
            ],
        },
        "x": 0, "y": 0, "w": 500,
    }
    node_result = node_golden.call({"kind": "layoutScreens", **case})
    py_result = layout_screens({k: v for k, v in case.items() if k not in ("x", "y", "w")}, case["x"], case["y"], case["w"], _width_of, "phrase")
    for key in ("x", "y", "w", "h", "prims", "anchors"):
        assert py_result.get(key) == node_result.get(key), key


def test_map_marker_robot_glyph_raises():
    with pytest.raises(NotImplementedError):
        layout_wireframe({"root": {"t": "map", "markers": [{"x": 0.5, "y": 0.5, "shape": "square"}]}}, 0, 0, 400, _width_of, "phrase")


def test_unknown_node_type_raises():
    with pytest.raises(ValueError):
        layout_wireframe({"root": {"t": "nope"}}, 0, 0, 400, _width_of, "phrase")
