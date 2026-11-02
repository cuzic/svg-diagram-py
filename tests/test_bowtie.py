"""Golden-master tests for bowtie_band()/layout_bowtie()/render_bowtie() against Node's
bowtie()/layoutBowtie()/renderBowtie() (all exported — live-tested via the shared dummy
width function, same technique as test_quadrant.py)."""

from __future__ import annotations

import pytest

from svg_diagram.bowtie import bowtie_band, layout_bowtie, render_bowtie

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {
        "input": {"top": "個人情報の漏えい", "threats": [{"label": "不正アクセス", "barriers": ["多要素認証", "アクセス制限"]}, {"label": "誤送信", "barriers": ["送信前の確認"]}], "consequences": [{"label": "信用の低下", "barriers": ["広報対応"]}, {"label": "賠償", "barriers": ["保険"]}]},
        "opts": {},
        "w": 1200,
    },
    {
        "input": {"hazard": "顧客データ", "top": "個人情報の漏えい", "threats": [{"label": "不正アクセス", "barriers": ["多要素認証", "アクセス制限"]}], "consequences": [{"label": "信用の低下", "barriers": ["広報対応"]}]},
        "opts": {},
        "w": 1200,
    },
    {
        "input": {"top": "停電", "threats": [{"label": "落雷"}, {"label": "設備故障", "barriers": ["定期点検"]}, {"label": "過負荷"}], "consequences": [{"label": "業務停止"}]},
        "opts": {},
        "w": 1000,
    },
    {
        "input": {"top": "ガス漏れ", "threats": [{"label": "配管腐食", "barriers": ["腐食防止"]}], "consequences": [{"label": "火災", "barriers": ["防火壁", "消火設備"]}]},
        "opts": {"maxNodeW": 140},
        "w": 900,
    },
    {
        "input": {"top": "長いイベント名のテスト" * 3, "threats": [{"label": "A"}], "consequences": [{"label": "B"}]},
        "opts": {"maxNodeW": "auto"},
        "w": 500,
    },
    {
        "input": {
            "top": "設備停止",
            "threats": [{"label": f"脅威{i}", "barriers": [f"バリア{i}-1", f"バリア{i}-2"]} for i in range(3)],
            "consequences": [{"label": f"結果{i}"} for i in range(2)],
        },
        "opts": {},
        "w": 1400,
    },
]


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["input"]["top"][:16])
def test_layout_bowtie_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutBowtie", "input": case["input"], "opts": case["opts"], "x": 0, "y": 0, "w": case["w"]})
    band = bowtie_band(case["input"], max_node_w=case["opts"].get("maxNodeW"))
    py_result = layout_bowtie(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    assert py_result == node_result


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: c["input"]["top"][:16])
def test_render_bowtie_matches_node(node_golden, case):
    band = bowtie_band(case["input"], max_node_w=case["opts"].get("maxNodeW"))
    laid = layout_bowtie(band, 0, 0, case["w"], _width_of, ROLES, "phrase")
    node_result = node_golden.call({"kind": "renderBowtie", "band": laid})
    py_result = render_bowtie(laid)
    assert py_result == node_result


def test_bowtie_rejects_missing_top():
    with pytest.raises(ValueError):
        bowtie_band({"top": "", "threats": [{"label": "a"}], "consequences": [{"label": "b"}]})


def test_bowtie_rejects_empty_threats():
    with pytest.raises(ValueError):
        bowtie_band({"top": "t", "threats": [], "consequences": [{"label": "b"}]})


def test_bowtie_rejects_blank_barrier():
    with pytest.raises(ValueError):
        bowtie_band({"top": "t", "threats": [{"label": "a", "barriers": ["  "]}], "consequences": [{"label": "b"}]})


def test_bowtie_rejects_bad_max_node_w():
    with pytest.raises(ValueError):
        bowtie_band({"top": "t", "threats": [{"label": "a"}], "consequences": [{"label": "b"}]}, max_node_w=10)


def test_bowtie_does_not_fit_raises():
    band = bowtie_band(
        {"top": "t", "threats": [{"label": "非常に長いラベルが入ったバリアのテスト" * 4}], "consequences": [{"label": "b"}]},
        max_node_w=200,
    )
    with pytest.raises(ValueError):
        layout_bowtie(band, 0, 0, 150, _width_of, ROLES, "phrase")
