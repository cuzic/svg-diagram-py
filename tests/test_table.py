"""Golden-master tests for layout_table()/render_table() against Node's layoutTable()/
renderTable() (both exported — live-tested via the shared dummy width function). Icon cells
not supported — see table.py's module docstring."""

import pytest

from svg_diagram.table import layout_table, render_table

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


CASES = [
    {"columns": [{"label": "項目", "flex": 1}, {"label": "値", "flex": 1}], "rows": [["速度", "速い"], ["コスト", "安い"]], "x": 0, "y": 0, "w": 600},
    {"columns": [{"label": "A"}, {"label": "B"}, {"label": "C"}], "rows": [[{"text": "x", "bold": True}, "y", {"text": "z", "mono": True}]], "x": 0, "y": 0, "w": 600},
    {"columns": [{"label": "名前"}, {"label": "結果"}], "rows": [[{"text": "ケース1"}, {"mark": "ok"}], [{"text": "ケース2"}, {"mark": "ng"}]], "x": 0, "y": 0, "w": 600},
    {"columns": [{"label": "A", "flex": 2}, {"label": "B", "flex": 1}], "rows": [["x", "y"]], "x": 0, "y": 0, "w": 600, "title": "タイトル"},
    {"columns": [{"label": "A"}, {"label": "B"}], "rows": [{"cells": ["x", "y"], "tone": "accent"}], "x": 0, "y": 0, "w": 600},
    {"columns": [{"label": "A"}, {"label": "B"}], "rows": [["x", "y"]], "x": 0, "y": 0, "w": 600, "rowHeader": True},
    {"columns": [{"label": "A"}, {"label": "B"}], "rows": [["x", "y"]], "x": 0, "y": 0, "w": 600, "dense": True},
    {"columns": [{}, {}, {}, {}], "rows": [["指標", "1月", "2月", "3月"]], "x": 0, "y": 0, "w": 600, "rowCurve": {"row": 0, "values": [10, 20, 15], "min": 0, "max": 30}, "header": False},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_layout_table_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutTable", **case})
    py_result = layout_table(
        columns=case["columns"], rows=case["rows"], x=case["x"], y=case["y"], w=case["w"], width_of=_width_of, roles=ROLES,
        width=case.get("width"), title=case.get("title"), dense=case.get("dense", False), header=case.get("header"),
        row_header=case.get("rowHeader", False), row_curve=case.get("rowCurve"),
    )
    for key in ("x", "y", "w", "h", "titleBar", "rows", "colX", "colW"):
        assert py_result.get(key) == node_result.get(key), key
    if "rowCurve" in node_result or "rowCurve" in py_result:
        assert py_result.get("rowCurve") == node_result.get("rowCurve")


def test_render_table_matches_node(node_golden):
    laid = layout_table(columns=[{"label": "項目", "flex": 1}, {"label": "値", "flex": 1}], rows=[["速度", "速い"], ["コスト", "安い"]], x=0, y=0, w=600, width_of=_width_of, roles=ROLES)
    node_result = node_golden.call({"kind": "renderTable", "band": laid})
    py_result = render_table(laid, roles=ROLES)
    assert py_result == node_result


def test_render_table_with_title_matches_node(node_golden):
    laid = layout_table(columns=[{"label": "A"}, {"label": "B"}], rows=[["x", "y"]], x=0, y=0, w=600, width_of=_width_of, roles=ROLES, title="タイトル")
    node_result = node_golden.call({"kind": "renderTable", "band": laid})
    py_result = render_table(laid, roles=ROLES)
    assert py_result == node_result
