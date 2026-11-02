"""Golden-master tests for layout_sequence()/render_sequence() against Node's
layoutSequence()/renderSequence() (both exported — live-tested via the shared dummy width
function). Actor icons not supported — see sequence.py's module docstring."""

import pytest

from svg_diagram.sequence import layout_sequence, render_sequence

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


ACTORS = [{"id": "u", "label": "ユーザー"}, {"id": "s", "label": "サーバー"}]

CASES = [
    {"actors": ACTORS, "steps": [{"from": "u", "to": "s", "label": "リクエスト"}, {"from": "s", "to": "u", "label": "レスポンス"}], "x": 0, "y": 0, "w": 600},
    {"actors": ACTORS, "steps": [{"self": "u", "label": "自己呼び出し"}], "x": 0, "y": 0, "w": 600},
    {"actors": ACTORS, "steps": [{"note": "これは注記です", "over": "u"}], "x": 0, "y": 0, "w": 600},
    {"actors": ACTORS, "steps": [{"note": "両方にかかる注記", "over": ["u", "s"]}], "x": 0, "y": 0, "w": 600},
    {"actors": ACTORS, "steps": [{"divider": "区切り"}], "x": 0, "y": 0, "w": 600},
    {"actors": ACTORS, "steps": [{"from": "u", "to": "s", "label": "x", "line": "dashed", "arrow": "both"}], "x": 0, "y": 0, "w": 600},
    {"actors": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}], "steps": [{"from": "a", "to": "c", "label": "長いメッセージラベルです"}], "x": 0, "y": 0, "w": 900},
    {"actors": ACTORS, "steps": [{"from": "u", "to": "s", "label": "番号なし", "number": False}], "x": 0, "y": 0, "w": 600, "numbered": True},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_layout_sequence_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutSequence", **case})
    py_result = layout_sequence(actors=case["actors"], steps=case["steps"], x=case["x"], y=case["y"], w=case["w"], width_of=_width_of, roles=ROLES, numbered=case.get("numbered", True))
    for key in ("x", "y", "w", "h", "heads", "steps", "lifeTop", "lifeBottom"):
        assert py_result.get(key) == node_result.get(key), key


def test_render_sequence_matches_node(node_golden):
    laid = layout_sequence(actors=ACTORS, steps=[{"from": "u", "to": "s", "label": "リクエスト"}, {"from": "s", "to": "u", "label": "レスポンス"}], x=0, y=0, w=600, width_of=_width_of, roles=ROLES)
    node_result = node_golden.call({"kind": "renderSequence", "band": laid})
    py_result = render_sequence(laid, roles=ROLES)
    assert py_result == node_result


def test_sequence_self_message_raises():
    with pytest.raises(ValueError):
        layout_sequence(actors=ACTORS, steps=[{"from": "u", "to": "u", "label": "x"}], x=0, y=0, w=600, width_of=_width_of, roles=ROLES)
