"""Golden-master tests for render_legend()/render_legend_item() against Node's renderLegend()
(swatch/line/and/back/blocks branches only — see legend.py's module docstring for what's
deferred)."""

import pytest

from svg_diagram.legend import render_legend_item
from svg_diagram.tokens import ROLES


def _node_item(case: dict) -> dict:
    """Translates this port's flat {kind, ...} item into Node's LaidOutLegendItem shape,
    which picks its rendering branch by which fields are present/truthy, not by a `kind`
    discriminant."""
    x, y, label = case["x"], case["y"], case["label"]
    kind = case["kind"]
    if kind == "swatch":
        return {"x": x, "y": y, "label": label, "swatch": {"tone": case.get("tone"), "dashed": case.get("dashed"), "double": case.get("double")}, "mark": case.get("mark")}
    if kind == "line":
        return {"x": x, "y": y, "label": label, "line": case.get("line") or "solid", "arrow": case.get("arrow", "end")}
    if kind in ("and", "back", "blocks"):
        return {"x": x, "y": y, "label": label, "edge": kind}
    raise ValueError(kind)


CASES = [
    {"kind": "swatch", "x": 10, "y": 20, "label": "accent", "tone": "accent"},
    {"kind": "swatch", "x": 10, "y": 20, "label": "danger dashed", "tone": "danger", "dashed": True},
    {"kind": "swatch", "x": 10, "y": 20, "label": "mark", "tone": "plain", "mark": True},
    {"kind": "swatch", "x": 10, "y": 20, "label": "double", "tone": "accent", "double": True},
    {"kind": "line", "x": 10, "y": 20, "label": "straight"},
    {"kind": "line", "x": 10, "y": 20, "label": "dashed", "line": "dashed"},
    {"kind": "line", "x": 10, "y": 20, "label": "dotted both", "line": "dotted", "arrow": "both"},
    {"kind": "line", "x": 10, "y": 20, "label": "no arrow", "arrow": "none"},
    {"kind": "and", "x": 10, "y": 20, "label": "AND"},
    {"kind": "back", "x": 10, "y": 20, "label": "return"},
    {"kind": "blocks", "x": 10, "y": 20, "label": "blocks"},
    {"kind": "swatch", "x": 11, "y": 23, "label": "日本語ラベル", "tone": "muted"},
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: str(c))
def test_render_legend_item_matches_node(node_golden, case):
    node_result = node_golden.call({"kind": "renderLegend", "items": [_node_item(case)]})
    opts = {k: v for k, v in case.items() if k not in ("x", "y", "label", "kind")}
    py_result = render_legend_item(x=case["x"], y=case["y"], label=case["label"], kind=case["kind"], note_size=ROLES["note"], **opts)
    assert py_result == node_result


def test_render_legend_item_strong_line_raises():
    with pytest.raises(NotImplementedError):
        render_legend_item(x=0, y=0, label="x", kind="line", weight="strong")
