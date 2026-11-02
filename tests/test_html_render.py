"""Tests for render_html() — spec section 7. New Python-only code, no Node counterpart."""

import base64
import re

from svg_diagram import Diagram
from svg_diagram.render_html import render_html


def _simple_svg() -> str:
    d = Diagram(width=300, height=120)
    d.box("Start", x=20, y=20, width=100, height=60)
    return d.render_svg()


def test_html_contains_viewport_meta():
    html = render_html(_simple_svg())
    assert 'name="viewport"' in html
    assert "width=device-width" in html


def test_html_inlines_the_svg_verbatim():
    svg = _simple_svg()
    html = render_html(svg)
    assert svg in html


def test_html_download_link_decodes_back_to_the_same_svg():
    svg = _simple_svg()
    html = render_html(svg, download_name="diagram.svg")
    m = re.search(r'href="data:image/svg\+xml;base64,([^"]+)"', html)
    assert m, "download link with a base64 data: URI not found"
    decoded = base64.b64decode(m.group(1)).decode("utf-8")
    assert decoded == svg


def test_html_download_attribute_names_the_svg_file():
    html = render_html(_simple_svg(), download_name="my-diagram.svg")
    assert 'download="my-diagram.svg"' in html
