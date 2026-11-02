"""Golden-master tests for layout_gantt()/render_gantt() against Node's layoutGantt()/
renderGantt() (both exported — live-tested via the shared dummy width function)."""

import pytest

from svg_diagram.gantt import layout_gantt, render_gantt

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


CASES = [
    {"rows": [{"section": "設計"}, {"label": "要件定義", "id": "req", "start": "2026-01-01", "days": 5}, {"label": "実装", "start": "2026-01-06", "days": 10, "after": "req"}, {"label": "リリース", "start": "2026-01-16", "milestone": True}], "x": 0, "y": 0, "w": 900},
    {"rows": [{"label": "A", "start": "2026-01-01", "end": "2026-01-10", "progress": 0.5, "tone": "danger"}, {"label": "B", "start": "2026-01-05", "end": "2026-01-20"}], "x": 0, "y": 0, "w": 900, "today": "2026-01-08"},
    {"rows": [{"label": "一", "id": "a", "start": "2026-01-01", "days": 3}, {"label": "二", "id": "b", "start": "2026-01-01", "days": 3, "after": "a"}, {"label": "三", "start": "2026-01-10", "days": 3, "after": ["a", "b"]}], "x": 0, "y": 0, "w": 900},
    {"rows": [{"label": "長期タスク", "start": "2025-01-01", "end": "2026-06-01"}], "x": 0, "y": 0, "w": 900},  # > SHORT_AXIS -> month ticks
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_layout_gantt_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutGantt", **case})
    py_result = layout_gantt(rows=case["rows"], x=case["x"], y=case["y"], w=case["w"], width_of=_width_of, roles=ROLES, from_=case.get("from"), to=case.get("to"), today=case.get("today"), today_label=case.get("todayLabel"), extend_to_today=case.get("extendToToday", False))
    for key in ("x", "y", "w", "h", "plot", "ticks", "sections", "bars", "deps", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key
    if "today" in node_result or "today" in py_result:
        assert py_result.get("today") == node_result.get("today")


def test_render_gantt_matches_node(node_golden):
    rows = [{"section": "設計"}, {"label": "要件定義", "id": "req", "start": "2026-01-01", "days": 5}, {"label": "実装", "start": "2026-01-06", "days": 10, "after": "req"}, {"label": "リリース", "start": "2026-01-16", "milestone": True}]
    laid = layout_gantt(rows=rows, x=0, y=0, w=900, width_of=_width_of, roles=ROLES)
    node_result = node_golden.call({"kind": "renderGantt", "band": laid})
    py_result = render_gantt(laid)
    assert py_result == node_result


def test_gantt_cycle_detection_raises():
    rows = [{"label": "a", "id": "a", "start": "2026-01-01", "days": 1, "after": "b"}, {"label": "b", "id": "b", "start": "2026-01-01", "days": 1, "after": "a"}]
    with pytest.raises(ValueError):
        layout_gantt(rows=rows, x=0, y=0, w=900, width_of=_width_of, roles=ROLES)
