"""Golden-master tests for layout_cloud_band()/render_cloud() against Node's
layoutCloudBand()/renderCloud() (both exported — live-tested via the shared dummy width
function)."""

import pytest

from svg_diagram.cloud import layout_cloud_band, render_cloud

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


BOXES = {"a": "共通の目的を達成する", "b": "品質を保つ", "c": "速度を保つ", "d": "レビューを徹底する", "d2": "レビューを省略する"}

CASES = [
    {"boxes": BOXES, "x": 0, "y": 0, "w": 900},
    {"boxes": {"a": "A", "b": {"text": "B", "tone": "danger", "id": "bNode"}, "c": "C", "d": "D", "d2": "D2"}, "x": 0, "y": 0, "w": 900},
    {"boxes": BOXES, "x": 0, "y": 0, "w": 900, "assumptions": [{"on": "ab", "text": "仮定1"}, {"on": "dd", "text": "仮定2", "injection": "施策A"}]},
    {"boxes": BOXES, "x": 0, "y": 0, "w": 900, "conflictLabel": "対立"},
    {"boxes": BOXES, "x": 20, "y": 10, "w": 800, "maxNodeW": 180},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_layout_cloud_band_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutCloudBand", **case["boxes"], **{k: v for k, v in case.items() if k != "boxes"}})
    py_result = layout_cloud_band(boxes=case["boxes"], x=case["x"], y=case["y"], w=case["w"], width_of=_width_of, roles=ROLES, max_node_w=case.get("maxNodeW"), assumptions=case.get("assumptions"), conflict_label=case.get("conflictLabel"))
    for key in ("x", "y", "w", "h", "nodes", "edges", "chips", "texts", "anchors", "labelBoxes"):
        assert py_result.get(key) == node_result.get(key), key


def test_render_cloud_matches_node(node_golden):
    laid = layout_cloud_band(boxes=BOXES, x=0, y=0, w=900, width_of=_width_of, roles=ROLES)
    node_result = node_golden.call({"kind": "renderCloud", "band": laid})
    py_result = render_cloud(laid)
    assert py_result == node_result


def test_cloud_too_narrow_raises():
    with pytest.raises(ValueError):
        layout_cloud_band(boxes=BOXES, x=0, y=0, w=200, width_of=_width_of, roles=ROLES)
