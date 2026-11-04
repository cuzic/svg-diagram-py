"""Golden-master tests for bars_band()/layout_bars()/render_bars() against Node's
bars()/layoutBars()/renderBars() (all exported — live-tested via the shared dummy width
function, same technique as test_flow_shapes.py / test_wordart.py)."""

import pytest

from svg_diagram.bars import bars_band, layout_bars, render_bars

ROLES = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}


def _width_of(atom: str, size=None, weight=None, font=None) -> float:
    return len(atom) * 8


LAYOUT_CASES = [
    {"data": [{"label": "A", "value": 10}, {"label": "B", "value": 25}, {"label": "C", "value": 15}], "opts": {}, "w": 600},
    {"data": [{"label": "A", "value": 10}, {"label": "B", "value": 25}, {"label": "C", "value": 15}], "opts": {"dir": "v"}, "w": 400},
    {"data": [{"label": "A", "value": 10, "series": "a"}, {"label": "B", "value": 25, "series": "b"}], "opts": {"stack": True}, "w": 600},
    {"data": [{"label": "A", "value": 10}, {"label": "B", "value": 25}], "opts": {"dir": "v", "stack": True}, "w": 400},
    {"data": [{"label": "A", "value": 100}, {"label": "B", "value": 60}, {"label": "C", "value": 40}], "opts": {"dir": "v", "cumulative": {}, "max": 200}, "w": 500},
    {"data": [{"label": "A", "value": 10}, {"label": "B", "value": 25}, {"label": "C", "value": 15}], "opts": {"dir": "v", "labelRole": "banner", "barRatio": 0.9, "lines": [{"at": 20, "label": "目標"}], "vlines": [{"at": 1.5, "label": "境界"}]}, "w": 400},
    {"data": [{"label": "低", "range": [3, 8]}, {"label": "高", "range": [10, 20]}], "opts": {"dir": "v", "max": 25}, "w": 400},
    {"data": [{"label": "A", "value": 5}, {"label": "B", "value": 9}, {"label": "C", "value": 2}], "opts": {"dir": "v", "edges": ["a", "b", "c", "d"], "hideZero": True}, "w": 400},
    {"data": [{"label": "A", "value": 10}, {"label": "B", "value": 25}], "opts": {"plotInset": [60, 60]}, "w": 600},
    {"data": [{"label": "A", "value": 10}, {"label": "B", "value": 25}], "opts": {"grid": False, "baseline": False}, "w": 600},
    # non-integer values >= 1000 with no valueFormat: exercises valueNum()'s toPrecision(whole) branch
    # (bars.py's _value_num -> _to_precision; this branch had a dormant NameError, see commit fixing it)
    {"data": [{"label": "A", "value": 1234.5}, {"label": "B", "value": 9876.25}], "opts": {"max": 20000}, "w": 700},
]

_PY_KW = {"dir": "direction", "max": "max_value", "labelRole": "label_role", "barRatio": "bar_ratio", "hideZero": "hide_zero", "plotInset": "plot_inset", "valueFormat": "value_format"}


def _py_opts(opts: dict) -> dict:
    out = {}
    for k, v in opts.items():
        out[_PY_KW.get(k, k)] = tuple(v) if k == "plotInset" else v
    return out


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_layout_bars_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "layoutBars", "data": case["data"], "x": 0, "y": 0, "w": case["w"], "opts": case["opts"]})
    band = bars_band(case["data"], **_py_opts(case["opts"]))
    py_result = layout_bars(band, 0, 0, case["w"], _width_of, ROLES)
    for key in ("x", "y", "w", "h", "dir", "stack", "bars", "ticks", "texts", "labelBoxes", "anchors", "ink"):
        assert py_result.get(key) == node_result.get(key), key


@pytest.mark.parametrize("case", LAYOUT_CASES, ids=lambda c: str(c["opts"]))
def test_render_bars_matches_node(node_golden, case):
    band = bars_band(case["data"], **_py_opts(case["opts"]))
    laid = layout_bars(band, 0, 0, case["w"], _width_of, ROLES)
    node_result = node_golden.call({"kind": "renderBars", "band": laid})
    py_result = render_bars(laid)
    assert py_result == node_result


def test_bars_rejects_empty_data():
    with pytest.raises(ValueError):
        bars_band([])


def test_bars_rejects_exceeding_max():
    with pytest.raises(ValueError):
        bars_band([{"label": "A", "value": 10}], max_value=5)
