"""End-to-end test cases from the ChatGPT-authored spec, section 8, adapted to
this MVP's absolute-coordinate scope (no auto-layout: "long text" means the
caller passes several lines, not that text wraps automatically)."""

import xml.dom.minidom as minidom

import pytest

from svg_diagram import Diagram


def _assert_well_formed_xml(svg: str) -> None:
    minidom.parseString(svg)  # raises xml.parsers.expat.ExpatError if malformed


def test_two_boxes_one_arrow():
    d = Diagram(width=600, height=200)
    start = d.box("Start", x=40, y=60, width=160, height=70, tone="accent")
    end = d.box("End", x=380, y=60, width=160, height=70, tone="new")
    d.arrow(start, end)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert svg.count("<rect") >= 2  # background rect + 2 boxes (snap4 may zero-width in pathological cases, not here)
    assert "marker-end" in svg


def test_multiple_nodes_and_arrows():
    d = Diagram(width=800, height=400)
    a = d.box("A", x=20, y=20, width=120, height=60)
    b = d.box("B", x=220, y=20, width=120, height=60)
    c = d.box("C", x=420, y=20, width=120, height=60)
    e = d.box("D", x=220, y=220, width=120, height=60)
    d.arrow(a, b)
    d.arrow(b, c)
    d.arrow(b, e, style="both")
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    # 3 connector <path>s plus 1 inside the <marker> arrowhead definition
    assert svg.count("<path") == 4
    assert svg.count("marker-end") == 3


def test_japanese_labels():
    d = Diagram(width=400, height=200)
    d.box("開始", x=20, y=20, width=160, height=70)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "開始" in svg


def test_long_text_as_multiple_lines():
    # no auto-wrap in this MVP: the caller supplies pre-broken lines
    d = Diagram(width=400, height=200)
    d.box(["これは長いラベルの", "一行目です", "そして二行目です"], x=20, y=20, width=200, height=100)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert svg.count("<text") == 3


def test_special_characters_are_escaped():
    d = Diagram(width=400, height=200)
    d.box('A & B < C > "D"', x=20, y=20, width=300, height=70)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    # & < > are entity-escaped in XML text content; a bare quote is valid there (only escape_attr, used for
    # attribute values, escapes quotes too — see emit_common.escape_attr) and matches Node's escapeXml exactly.
    assert "&quot;D&quot;" not in svg  # i.e. quotes are NOT escaped in text content
    assert "A &amp; B &lt; C &gt; \"D\"" in svg


def test_overlapping_shapes_are_allowed():
    d = Diagram(width=300, height=200)
    d.box("Back", x=20, y=20, width=200, height=150, tone="muted")
    d.box("Front", x=60, y=60, width=100, height=60, tone="accent")
    svg = d.render_svg()
    _assert_well_formed_xml(svg)


def test_empty_diagram_is_still_valid_svg():
    d = Diagram(width=300, height=200)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert '<svg xmlns="http://www.w3.org/2000/svg"' in svg


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width": 0, "height": 100},
        {"width": 100, "height": -1},
        {"width": -10, "height": -10},
    ],
)
def test_invalid_diagram_dimensions_raise(kwargs):
    with pytest.raises(ValueError):
        Diagram(**kwargs)


def test_invalid_box_dimensions_raise():
    d = Diagram(width=300, height=200)
    with pytest.raises(ValueError):
        d.box("x", x=0, y=0, width=0, height=10)


def test_duplicate_box_id_raises():
    d = Diagram(width=300, height=200)
    d.box("A", x=0, y=0, width=50, height=50, id="dup")
    with pytest.raises(ValueError):
        d.box("B", x=100, y=0, width=50, height=50, id="dup")


def test_arrow_to_unknown_id_raises():
    d = Diagram(width=300, height=200)
    a = d.box("A", x=0, y=0, width=50, height=50)
    with pytest.raises(ValueError):
        d.arrow(a, "does-not-exist")


def test_repeated_run_is_deterministic():
    def build() -> str:
        d = Diagram(width=600, height=200)
        start = d.box("Start", x=40, y=60, width=160, height=70, tone="accent")
        end = d.box("End", x=380, y=60, width=160, height=70, tone="new")
        d.arrow(start, end)
        return d.render_svg()

    assert build() == build()
