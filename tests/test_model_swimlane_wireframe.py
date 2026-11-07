"""End-to-end tests for the Diagram.swimlane()/.wireframe()/.screens() methods added in
this change (model_shapes.py's _Swimlane/_Wireframe/_Screens) — the composed-level Diagram
API around swimlane.py/wireframe.py's already golden-tested layout_X()/render_X() pair.
Python-only at this composed level (same reasoning as test_model_extensions.py)."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _assert_well_formed_xml(svg: str) -> None:
    minidom.parseString(svg)


def test_swimlane_via_diagram():
    d = Diagram(600, 300)
    d.swimlane(
        lanes=[{"id": "cust", "label": "顧客"}, {"id": "ops", "label": "運用"}],
        steps=[{"id": "order", "lane": "cust", "col": 1, "span": 1, "title": "注文する"}, {"id": "ship", "lane": "ops", "col": 2, "span": 1, "title": "発送する"}],
        x=0, y=0, width=600, cols=2,
    )
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "注文する" in svg and "発送する" in svg


def test_wireframe_via_diagram():
    d = Diagram(400, 200)
    d.wireframe({"t": "col", "children": [{"t": "text", "text": "ログイン"}, {"t": "btn", "label": "送信", "primary": True}]}, x=0, y=0, width=400, height=150)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "ログイン" in svg and "送信" in svg


def test_screens_grid_via_diagram():
    d = Diagram(700, 400)
    d.screens([{"title": "画面A", "root": {"t": "text", "text": "A"}}, {"title": "画面B", "root": {"t": "text", "text": "B"}}], x=0, y=0, width=700)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "画面A" in svg and "画面B" in svg


def test_screens_matrix_via_diagram():
    d = Diagram(500, 300)
    d.screens(x=0, y=0, width=500, matrix={"cols": ["通常", "異常"], "rows": [{"label": "部品X", "cells": [{"t": "text", "text": "OK"}, "na"]}]})
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "部品X" in svg and "対象外" in svg
