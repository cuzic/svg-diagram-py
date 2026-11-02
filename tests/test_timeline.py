"""Golden-master tests for layout_timeline()/render_timeline() against Node's
layoutTimeline()/renderTimeline() (both exported — live-tested via the shared dummy width
function). The numeric-axis variant is NOT ported (see timeline.py's module docstring)."""

import pytest

from svg_diagram.timeline import layout_timeline, render_timeline

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


CASES = [
    {"now": {"at": "2026-01-01"}, "deadline": {"label": "リリース", "at": "2026-06-30"}, "marks": [{"label": "中間レビュー", "at": "2026-03-15"}], "from": "2026-01-01", "to": "2026-12-31", "x": 0, "y": 0, "w": 900},
    {"now": {"at": "2026-01-01"}, "deadline": {"label": "期限", "at": "2026-02-01", "line": "full"}, "marks": [], "from": "2025-12-01", "to": "2026-03-01", "x": 0, "y": 0, "w": 700},
    {"now": {"at": "2026-06-01", "label": "今"}, "deadline": {"label": "完了", "at": "2026-01-01"}, "marks": [], "from": "2026-01-01", "to": "2026-12-31", "x": 0, "y": 0, "w": 800},
    {"now": {"at": "2026-01-01"}, "deadline": {"label": "D", "at": "2026-01-01"}, "marks": [], "from": "2026-01-01", "to": "2026-12-31", "x": 0, "y": 0, "w": 800},  # same day (merged flag)
    {"now": {"at": "2026-01-01"}, "deadline": {"label": "期限", "at": "2026-12-31"}, "marks": [], "from": "2026-01-01", "to": "2026-12-31", "x": 10, "y": 20, "w": 900, "span": "fill", "remaining": False},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_layout_timeline_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutTimeline", **case})
    py_result = layout_timeline(
        now=case["now"], deadline=case["deadline"], marks=case.get("marks"), from_=case["from"], to=case["to"],
        span=case.get("span"), remaining=case.get("remaining"), x=case["x"], y=case["y"], w=case["w"], width_of=_width_of, roles=ROLES,
    )
    for key in ("x", "y", "w", "h", "axis", "ticks", "stems", "dots", "texts", "labelBoxes", "span"):
        assert py_result.get(key) == node_result.get(key), key
    if "bracket" in node_result or "bracket" in py_result:
        assert py_result.get("bracket") == node_result.get("bracket")
    if "fullLine" in node_result or "fullLine" in py_result:
        assert py_result.get("fullLine") == node_result.get("fullLine")


def test_render_timeline_matches_node(node_golden):
    laid = layout_timeline(
        now={"at": "2026-01-01"}, deadline={"label": "リリース", "at": "2026-06-30"}, marks=[{"label": "中間レビュー", "at": "2026-03-15"}],
        from_="2026-01-01", to="2026-12-31", span=None, remaining=None, x=0, y=0, w=900, width_of=_width_of, roles=ROLES,
    )
    node_result = node_golden.call({"kind": "renderTimeline", "band": laid})
    py_result = render_timeline(laid)
    assert py_result == node_result


def test_timeline_too_narrow_raises():
    from svg_diagram.timeline import layout_timeline as lt

    with pytest.raises(ValueError):
        lt(now={"at": "2026-01-01"}, deadline={"label": "x", "at": "2026-02-01"}, marks=[], from_="2026-01-01", to="2026-03-01", span=None, remaining=None, x=0, y=0, w=100, width_of=_width_of, roles=ROLES)
