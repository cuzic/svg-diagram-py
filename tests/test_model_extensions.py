"""End-to-end tests for the new Diagram features: box() extensions (step/tag/stamp/
frame/dim/raw), caption()/group()/banner(), legend(), row()/grid(). These exercise
model.py's composition (new, Python-only, not golden-tested at this level — the
primitives it calls are) via XML well-formedness and basic structural checks."""

import xml.dom.minidom as minidom

from svg_diagram import Diagram


def _assert_well_formed_xml(svg: str) -> None:
    minidom.parseString(svg)


def test_box_with_step_badge():
    d = Diagram(width=400, height=200)
    d.box("手順1", x=20, y=20, width=200, height=70, step=1, tone="accent")
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert 'data-badge=""' in svg
    assert "手順 1" in svg


def test_box_with_tag():
    d = Diagram(width=400, height=200)
    d.box("Feature", x=20, y=40, width=200, height=70, tag="NEW", tag_tone="danger")
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "NEW" in svg


def test_box_with_stamp():
    d = Diagram(width=400, height=200)
    d.box("Draft doc", x=20, y=20, width=200, height=70, stamp="draft")
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "draft" in svg


def test_box_frame_false_has_no_rect_but_has_text():
    d = Diagram(width=400, height=200)
    d.box("No frame", x=20, y=20, width=200, height=70, frame=False)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert svg.count("<rect") == 1  # only the page background rect, no box frame
    assert "No frame" in svg


def test_box_dim():
    d = Diagram(width=400, height=200)
    d.box("Dimmed", x=20, y=20, width=200, height=70, tone="accent", dim=True)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "#6f6659" in svg  # PALETTE.muted stroke when dim


def test_raw_escape_hatch():
    d = Diagram(width=400, height=200)
    d.raw(x=20, y=20, width=100, height=100, draw=lambda ctx: f'<circle cx="{ctx["x"] + 50}" cy="{ctx["y"] + 50}" r="20" fill="{ctx["color"]("accent")}"/>')
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "<circle" in svg


def test_caption():
    d = Diagram(width=400, height=200)
    d.caption("図のタイトル", x=0, y=30, width=400, align="left")
    d.box("A", x=20, y=40, width=100, height=60)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "図のタイトル" in svg


def test_group_with_title_and_children():
    d = Diagram(width=400, height=300)
    d.group(x=10, y=10, width=380, height=200, title="グループ", tone="muted")
    d.box("inside", x=30, y=50, width=100, height=60)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "グループ" in svg
    assert "inside" in svg


def test_banner():
    d = Diagram(width=400, height=200)
    d.banner("重要なお知らせ", x=0, y=0, width=400, height=60)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "重要なお知らせ" in svg
    assert "#ffffff" in svg  # white text on the accent-filled banner


def test_legend():
    d = Diagram(width=400, height=200)
    d.legend(
        [
            {"x": 20, "y": 150, "label": "通常", "kind": "swatch", "tone": "plain"},
            {"x": 20, "y": 174, "label": "強調", "kind": "swatch", "tone": "accent"},
            {"x": 150, "y": 150, "label": "依存", "kind": "line"},
        ]
    )
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "通常" in svg and "強調" in svg and "依存" in svg


def test_row_equal_distribution():
    d = Diagram(width=600, height=200)
    boxes = d.row([{"label": "A"}, {"label": "B"}, {"label": "C"}], x=0, y=20, width=600, height=60, justify="stretch")
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert len(boxes) == 3
    # grid-snapped equal distribution: symmetric (first == last), the odd leftover grid
    # step (if any) goes to the middle column, so it may differ from the outer two by one
    # 4px grid step — see layout_util.grid_columns()'s "odd" handling.
    assert boxes[0].width == boxes[2].width
    assert abs(boxes[1].width - boxes[0].width) <= 4


def test_row_with_arrows():
    d = Diagram(width=600, height=200)
    d.row([{"label": "A"}, {"label": "B"}, {"label": "C"}], x=0, y=20, width=600, height=60, justify="stretch", arrows=True)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert svg.count("marker-end") == 2  # 2 arrows between 3 boxes


def test_grid_wraps_rows():
    d = Diagram(width=600, height=400)
    boxes = d.grid([{"label": str(i)} for i in range(5)], x=0, y=0, width=600, row_height=60, cols=3)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert len(boxes) == 5
    # 5 boxes over 3 columns -> 2 rows; boxes[3] starts a new row (same y origin col as boxes[0])
    assert boxes[3].x == boxes[0].x
    assert boxes[3].y > boxes[0].y


def test_arrow_with_label():
    d = Diagram(width=400, height=200)
    a = d.box("A", x=20, y=20, width=100, height=60)
    b = d.box("B", x=250, y=20, width=100, height=60)
    d.arrow(a, b, label="depends on")
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "depends on" in svg


def test_arrow_with_chip_label():
    d = Diagram(width=400, height=200)
    a = d.box("A", x=20, y=20, width=100, height=60)
    b = d.box("B", x=250, y=20, width=100, height=60)
    d.arrow(a, b, label="uses", chip=True)
    svg = d.render_svg()
    _assert_well_formed_xml(svg)
    assert "uses" in svg
    assert svg.count("<rect") >= 2  # bg rect + at least the box rects + chip rect
