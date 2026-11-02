"""The absolute-coordinate Diagram API — spec section 4/5, now covering box() extensions
(tag/stamp/step/frame/dim/raw), caption()/group()/banner(), legend(), and row()/grid().

Placement (x/y of every element) has NO Node.js counterpart: svg-diagram's real
box()/connect()/row()/grid() always go through the full auto-layout pipeline
(lib/pipeline.ts) and never accept an explicit x/y. This module is new, Python-only code
(not a port, not golden-tested at this composed level); it composes the ported
drawing-layer primitives in emit_boxes.py/emit_common.py/emit.py/badge.py/legend.py, which
ARE golden-tested against Node — EXCEPT row()/grid()'s child-width distribution
(layout_util.py's grid_columns/row_child_geometry/grid_child_geometry), which IS
golden-tested, because that one piece is pure arithmetic with no text-metrics dependency
(see the plan's Phase E notes) and so is byte-identical to Node, unlike everything else
here.

Padding/geometry constants (BOX_PAD_X, STEP_BADGE_R, TAG_H, ...) are copied from
lib/layout-util.ts for visual familiarity with Node's own look — that is a style choice,
not a compatibility requirement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Callable, Literal

from .approx_width import approx_width_of
from .emit import emit_svg
from .emit_boxes import render_banner, render_box_rect, render_caption, render_connect, render_group_rect, render_raw, render_status, render_step_badge, render_stamp, render_tag
from .emit_common import LH_EM, js_round, text_lines
from .figures import pyramid_layer_geometry, render_curve, render_pyramid
from .layout_util import BOX_PAD_X, BOX_PAD_Y, STAMP_PAD_X, STEP_INDENT, TAG_H, TAG_PAD_X, grid_child_geometry, row_child_geometry
from .legend import render_legend_item
from .cloud import layout_cloud_band, render_cloud
from .gantt import layout_gantt, render_gantt
from .people_dots import layout_dots, layout_people, render_dots, render_people
from .timeline import layout_timeline, render_timeline
from .flow_shapes import (
    chevron_band,
    concentric_band,
    cycle_band,
    funnel_band,
    layout_flow_shape,
    render_flow_shape,
    value_chain_band,
    venn_band,
)
from .sequence import layout_sequence, render_sequence
from .table import layout_table, render_table
from .tree import layout_tree_band, render_tree
from .wordart import layout_word_art, render_word_art, word_art_band
from .tokens import PALETTE, ROLES, best_text_color, blend_luminance, run_color_of, text_color_of
from .wrap import wrap_text

Tone = Literal["plain", "accent", "danger", "muted", "new", "changed", "removed", "solid", "solid-danger"]
ArrowStyle = Literal["start", "end", "both", "none"]
LineStyle = Literal["solid", "dashed", "dotted"]


@dataclass
class Box:
    id: str
    x: float
    y: float
    width: float
    height: float
    lines: list[str] = field(default_factory=list)
    tone: Tone | None = None
    fill: str | None = None
    stroke: str | None = None
    dashed: bool | None = None
    frame: bool = True
    dim: bool = False
    step: int | str | None = None
    tag: str | None = None
    tag_tone: Literal["accent", "danger", "muted"] | None = None
    tag_at: float = 1.0
    stamp: str | None = None


@dataclass
class Arrow:
    source: str
    target: str
    arrow: ArrowStyle = "end"
    line: LineStyle | None = None
    tone: Tone | None = None
    label: str | None = None
    chip: bool = False
    label_at: float = 0.5


@dataclass
class _Caption:
    x: float
    y: float
    w: float
    text: str
    align: str = "center"
    tone: Tone | None = None


@dataclass
class _Group:
    x: float
    y: float
    w: float
    h: float
    title: str | None = None
    tone: Tone | None = None
    dashed: bool | None = None
    dim: bool = False
    stamp: str | None = None


@dataclass
class _Banner:
    x: float
    y: float
    w: float
    h: float
    lines: list[str] = field(default_factory=list)
    tone: Tone | None = None


@dataclass
class _Legend:
    items: list[dict]


@dataclass
class _Raw:
    x: float
    y: float
    w: float
    h: float
    draw: Callable[[dict], str]


@dataclass
class _Pyramid:
    x: float
    y: float
    layers: list[str]
    width: float | None = None
    layer_height: float = 76
    apex_ratio: float = 0.3
    day: int | str = 1


@dataclass
class _Curve:
    x: float
    y: float
    width: float
    height: float
    points: list[dict]
    y_top_label: str | None = None
    y_bottom_label: str | None = None
    x_label: str | None = None
    day: int | str = 1


@dataclass
class _People:
    x: float
    y: float
    cw: float
    cols: int
    size: float
    gap: float
    total: int
    count: int
    count2: int = 0
    align: str | None = None
    side: dict | None = None
    tone: Tone | None = None
    tone2: Tone | None = None
    rest: Tone | None = "muted"
    alt: str = ""
    day: int | str = 1


@dataclass
class _Dots:
    x: float
    y: float
    cw: float
    r: float
    dots: list[dict]
    zones: list[dict]
    min_val: float
    max_val: float
    width: float | None = None
    low_label: str | None = None
    high_label: str | None = None
    height: float | None = None
    alt: str = ""
    day: int | str = 1


@dataclass
class _Timeline:
    x: float
    y: float
    w: float
    now: dict
    deadline: dict
    marks: list[dict] = field(default_factory=list)
    from_: str = ""
    to: str = ""
    span: str | None = None
    remaining: object = None
    day: int | str = 1


@dataclass
class _Gantt:
    x: float
    y: float
    w: float
    rows: list[dict]
    from_: str | None = None
    to: str | None = None
    today: str | None = None
    today_label: str | None = None
    extend_to_today: bool = False
    day: int | str = 1


@dataclass
class _Cloud:
    x: float
    y: float
    w: float
    boxes: dict
    max_node_w: float | None = None
    assumptions: list[dict] | None = None
    conflict_label: str | None = None
    day: int | str = 1


@dataclass
class _Tree:
    x: float
    y: float
    w: float
    root: dict
    dir_opt: str | None = None
    max_node_w: float | None = None
    balanced: bool = False
    layout_mode: str | None = None
    sides: dict | None = None
    edges_opt: str | bool | None = None
    day: int | str = 1


@dataclass
class _Table:
    x: float
    y: float
    w: float
    columns: list[dict]
    rows: list
    width: float | None = None
    title: str | None = None
    dense: bool = False
    header: bool | None = None
    row_header: bool = False
    header_h: float | None = None
    cell_h: float | None = None
    row_curve: dict | None = None
    day: int | str = 1


@dataclass
class _Sequence:
    x: float
    y: float
    w: float
    actors: list[dict]
    steps: list[dict]
    numbered: bool = True
    day: int | str = 1


@dataclass
class _FlowShape:
    x: float
    y: float
    cw: float
    band: dict
    day: int | str = 1


@dataclass
class _WordArt:
    x: float
    y: float
    cw: float
    band: dict
    day: int | str = 1


@dataclass
class _Status:
    x: float
    y: float
    width: float
    text: str
    status: str
    height: float = 24
    size: float = 14


def _edge_point(box: Box, side: str) -> dict:
    cx, cy = box.x + box.width / 2, box.y + box.height / 2
    return {
        "left": {"x": box.x, "y": cy},
        "right": {"x": box.x + box.width, "y": cy},
        "top": {"x": cx, "y": box.y},
        "bottom": {"x": cx, "y": box.y + box.height},
        "center": {"x": cx, "y": cy},
    }[side]


class Diagram:
    """spec section 4: ``Diagram(width, height)``, ``.box(...)``, ``.arrow(start, end)``, ``.save(path)``."""

    def __init__(self, width: int, height: int):
        if width <= 0 or height <= 0:
            raise ValueError(f"Diagram(width, height) must both be positive (got {width}, {height})")
        self.width = width
        self.height = height
        self.boxes: list[Box] = []
        self.arrows: list[Arrow] = []
        self._elements: list[object] = []
        self._ids = count(1)

    # ---- box() -----------------------------------------------------------------------

    def box(
        self,
        label: str | list[str] = "",
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        id: str | None = None,
        tone: Tone | None = None,
        fill: str | None = None,
        stroke: str | None = None,
        dashed: bool | None = None,
        frame: bool = True,
        dim: bool = False,
        step: int | str | None = None,
        tag: str | None = None,
        tag_tone: Literal["accent", "danger", "muted"] | None = None,
        tag_at: float = 1.0,
        stamp: str | None = None,
    ) -> Box:
        if width <= 0 or height <= 0:
            raise ValueError(f"box(): width and height must both be positive (got {width}, {height})")
        lines = label if isinstance(label, list) else ([label] if label else [])
        box_id = id or f"b{next(self._ids)}"
        if any(b.id == box_id for b in self.boxes):
            raise ValueError(f"box(): id {box_id!r} is already used")
        b = Box(
            id=box_id, x=x, y=y, width=width, height=height, lines=lines, tone=tone, fill=fill, stroke=stroke,
            dashed=dashed, frame=frame, dim=dim, step=step, tag=tag, tag_tone=tag_tone, tag_at=tag_at, stamp=stamp,
        )
        self.boxes.append(b)
        self._elements.append(b)
        return b

    def raw(self, *, x: float, y: float, width: float, height: float, draw: Callable[[dict], str]) -> None:
        """lib/dsl/text-bands.ts's raw(): the escape hatch for a shape this port has no primitive for."""
        self._elements.append(_Raw(x=x, y=y, w=width, h=height, draw=draw))

    def caption(self, text: str, *, x: float, y: float, width: float, align: str = "center", tone: Tone | None = None) -> None:
        self._elements.append(_Caption(x=x, y=y, w=width, text=text, align=align, tone=tone))

    def group(self, *, x: float, y: float, width: float, height: float, title: str | None = None, tone: Tone | None = None, dashed: bool | None = None, dim: bool = False, stamp: str | None = None) -> None:
        self._elements.append(_Group(x=x, y=y, w=width, h=height, title=title, tone=tone, dashed=dashed, dim=dim, stamp=stamp))

    def banner(self, label: str | list[str] = "", *, x: float, y: float, width: float, height: float, tone: Tone | None = None) -> None:
        lines = label if isinstance(label, list) else ([label] if label else [])
        self._elements.append(_Banner(x=x, y=y, w=width, h=height, lines=lines, tone=tone))

    def legend(self, items: list[dict]) -> None:
        """Each item: `{x, y, label, kind, ...}` — see legend.render_legend_item()."""
        self._elements.append(_Legend(items=items))

    def pyramid(self, layers: list[str], *, x: float, y: float, width: float | None = None, layer_height: float = 76, apex_ratio: float = 0.3) -> None:
        """lib/dsl/figures.ts's pyramid(): layers bottom-to-top, >= 2. The per-layer geometry
        (layout_pyramid's formula in figures.py) IS byte-identical to Node — it's pure closed-
        form arithmetic — but the text WRAPPING uses this port's approximate width function."""
        if len(layers) < 2:
            raise ValueError("pyramid(layers) needs at least 2 layers, bottom to top")
        self._elements.append(_Pyramid(x=x, y=y, layers=layers, width=width, layer_height=layer_height, apex_ratio=apex_ratio))

    def curve(self, points: list[dict], *, x: float, y: float, width: float, height: float, y_top_label: str | None = None, y_bottom_label: str | None = None, x_label: str | None = None) -> None:
        """lib/dsl/figures.ts's curve(): an axis + connected-dot trend line. Each point:
        `{y: 0..1, emphasis?, dropLine?}`, evenly spaced left-to-right. The point-placement
        formula (figures.curve_points) IS byte-identical to Node (pure closed-form arithmetic)."""
        if len(points) < 2:
            raise ValueError("curve(points) needs at least 2 points")
        self._elements.append(_Curve(x=x, y=y, width=width, height=height, points=points, y_top_label=y_top_label, y_bottom_label=y_bottom_label, x_label=x_label))

    def timeline(
        self,
        *,
        x: float,
        y: float,
        width: float,
        now: dict,
        deadline: dict,
        marks: list[dict] | None = None,
        from_: str,
        to: str,
        span: str | None = None,
        remaining: object = None,
    ) -> None:
        """lib/timeline.ts's timeline() (date-based only — see timeline.py's module
        docstring for the numeric-axis variant, not ported). `now`/`deadline`: {at, label?,
        line?}; `marks`: [{at, label, tone?}]. The layout formula (layout_timeline) IS
        byte-identical to Node (golden-tested live); only text widths use this port's
        approximation."""
        self._elements.append(_Timeline(x=x, y=y, w=width, now=now, deadline=deadline, marks=marks or [], from_=from_, to=to, span=span, remaining=remaining))

    def gantt(
        self,
        rows: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        from_: str | None = None,
        to: str | None = None,
        today: str | None = None,
        today_label: str | None = None,
        extend_to_today: bool = False,
    ) -> None:
        """lib/gantt.ts's gantt(): rows are tasks ({label, start, end|days|milestone, id?,
        after?, tone?, progress?}) or section headings ({section}). The layout formula
        (layout_gantt — axis placement, dependency-arrow routing, cycle detection) IS
        byte-identical to Node (golden-tested live); only label text widths use this port's
        approximation."""
        self._elements.append(_Gantt(x=x, y=y, w=width, rows=rows, from_=from_, to=to, today=today, today_label=today_label, extend_to_today=extend_to_today))

    def cloud(
        self,
        boxes: dict,
        *,
        x: float,
        y: float,
        width: float,
        max_node_w: float | None = None,
        assumptions: list[dict] | None = None,
        conflict_label: str | None = None,
    ) -> None:
        """lib/dsl/diagrams.ts's cloud(): TOC's evaporating cloud / 対立解消図. `boxes`:
        {a,b,c,d,d2} each a str or {text, id?, tone?}. The layout formula (layout_cloud_band —
        closed-form 3-column/2-row geometry, chip placement, zigzag conflict arrow) IS
        byte-identical to Node (golden-tested live); only text widths use this port's
        approximation."""
        self._elements.append(_Cloud(x=x, y=y, w=width, boxes=boxes, max_node_w=max_node_w, assumptions=assumptions, conflict_label=conflict_label))

    def tree(self, root: dict, *, x: float, y: float, width: float, dir: str | None = None, max_node_w: float | None = None) -> None:
        """lib/dsl/diagrams.ts's tree(): an org chart / hierarchy. `root`: {label, sub?, id?,
        tone?, children?}. The layout formula (layout_tree_band — tidy-tree centering, width x
        direction search) IS byte-identical to Node (golden-tested live); only text widths use
        this port's approximation. (Band-node children, `tree({band: ...})`, are not
        supported.)"""
        self._elements.append(_Tree(x=x, y=y, w=width, root=root, dir_opt=dir, max_node_w=max_node_w))

    def mindmap(
        self,
        root: dict,
        *,
        x: float,
        y: float,
        width: float,
        layout: str | None = None,
        sides: dict[str, str] | None = None,
        edges: str | bool | None = None,
        max_node_w: float | None = None,
    ) -> None:
        """lib/dsl/diagrams.ts's mindmap(): the same TreeBand as tree(), with `balanced: True`
        and layout/sides/edges flags (lib/dsl/diagrams.ts:473-483). `layout`: 'radial'
        (default) | 'right' | 'left' | 'down' | 'up' | 'org' | 'list' | 'brace' | 'fishbone' |
        'timeline'. The layout formula IS byte-identical to Node (golden-tested live)."""
        self._elements.append(_Tree(x=x, y=y, w=width, root=root, balanced=True, layout_mode=layout, sides=sides, edges_opt=edges, max_node_w=max_node_w))

    def table(
        self,
        columns: list[dict],
        rows: list,
        *,
        x: float,
        y: float,
        width: float,
        table_width: float | None = None,
        title: str | None = None,
        dense: bool = False,
        header: bool | None = None,
        row_header: bool = False,
        header_h: float | None = None,
        cell_h: float | None = None,
        row_curve: dict | None = None,
    ) -> None:
        """lib/dsl's table(): `columns`: [{label?, flex?, bold?, mono?, align?}]. `rows`: each a
        list of cells (str, {text,tone?,bold?,mono?,align?,mark?}) or {cells, tone?, h?}. The
        layout formula (layout_table) IS byte-identical to Node (golden-tested live); only text
        widths use this port's approximation. Icon cells are not supported."""
        self._elements.append(_Table(x=x, y=y, w=width, columns=columns, rows=rows, width=table_width, title=title, dense=dense, header=header, row_header=row_header, header_h=header_h, cell_h=cell_h, row_curve=row_curve))

    def sequence(self, actors: list[dict], steps: list[dict], *, x: float, y: float, width: float, numbered: bool = True) -> None:
        """lib/dsl's sequence(): a UML-style sequence diagram. `actors`: [{id, label, tone?}].
        `steps`: each {from,to,label,line?,arrow?,tone?} (msg) | {self,label,...} | {note,over}
        | {divider}. The layout formula (layout_sequence) IS byte-identical to Node (golden-
        tested live); only text widths use this port's approximation. Actor icons not
        supported."""
        self._elements.append(_Sequence(x=x, y=y, w=width, actors=actors, steps=steps, numbered=numbered))

    def chevron(self, steps: list[dict], *, x: float, y: float, width: float, direction: str | None = None, first: str | None = None, gap: float | None = None, current: int | None = None) -> None:
        """lib/flow-shapes.ts's chevron(): process arrows. `steps`: [{label, sub?, id?, tone?}].
        The layout formula IS byte-identical to Node (golden-tested live). loopBack arrows not
        supported."""
        band = chevron_band(steps, direction=direction, first=first, gap=gap, current=current)
        self._elements.append(_FlowShape(x=x, y=y, cw=width, band=band))

    def funnel(self, stages: list[dict], *, x: float, y: float, width: float, scale: str | None = None, show_rate: bool = False) -> None:
        """lib/flow-shapes.ts's funnel(): narrowing stages. `stages`: [{label, value?, id?, tone?}]."""
        band = funnel_band(stages, scale=scale, show_rate=show_rate)
        self._elements.append(_FlowShape(x=x, y=y, cw=width, band=band))

    def cycle(self, steps: list[dict], *, x: float, y: float, width: float, direction: str | None = None, centre: str | None = None) -> None:
        """lib/flow-shapes.ts's cycle(): a closed loop of 3-8 nodes. `steps`: [{label, sub?, id?, tone?}]."""
        band = cycle_band(steps, direction=direction, centre=centre)
        self._elements.append(_FlowShape(x=x, y=y, cw=width, band=band))

    def venn(self, sets: list[dict], *, x: float, y: float, width: float, overlaps: list[dict] | None = None, centre: str | None = None, universe: str | bool | None = None) -> None:
        """lib/flow-shapes.ts's venn(): 2 or 3 sets. `sets`: [{name, label?, id?, tone?}]."""
        band = venn_band(sets, overlaps=overlaps, centre=centre, universe=universe)
        self._elements.append(_FlowShape(x=x, y=y, cw=width, band=band))

    def concentric(self, rings: list[dict], *, x: float, y: float, width: float, order: str | None = None, labels: str | None = None, centre: str | None = None) -> None:
        """lib/flow-shapes.ts's concentric(): nested rings. `rings`: [{label, description?, id?, tone?}]."""
        band = concentric_band(rings, order=order, labels=labels, centre=centre)
        self._elements.append(_FlowShape(x=x, y=y, cw=width, band=band))

    def value_chain(self, *, primary: list[dict], x: float, y: float, width: float, support: list[dict] | None = None, margin: str | bool | None = None, titles: tuple | bool | None = None) -> None:
        """lib/flow-shapes.ts's valueChain(): Porter's value chain."""
        band = value_chain_band(support=support, primary=primary, margin=margin, titles=titles)
        self._elements.append(_FlowShape(x=x, y=y, cw=width, band=band))

    def wordart(
        self,
        text: str,
        *,
        x: float,
        y: float,
        width: float,
        id: str | None = None,
        style: str | None = None,
        writing: str | None = None,
        size: float | str | None = None,
        weight: str | None = None,
        font: str | None = None,
        tone: str | None = None,
        gradient: dict | None = None,
        outline=None,
        shadow=None,
        glow=None,
        bevel: bool | None = None,
        extrude=None,
        reflection=None,
        plate: str | None = None,
        spacing: float | None = None,
        arc: float | None = None,
        rotate: float | None = None,
        flip: str | None = None,
        align: str | None = None,
        limit: float | None = None,
    ) -> None:
        """lib/wordart.ts's wordart(): decorated headline text (bold/outline/shadow/sticker/
        glow/emboss/3d/gradient/reflect presets, bent along an arc, or set vertically/縦書き).
        The layout formula IS byte-identical to Node (golden-tested live); only text widths
        use this port's approximation."""
        band = word_art_band(
            text, id=id, style=style, writing=writing, size=size, weight=weight, font=font, tone=tone,
            gradient=gradient, outline=outline, shadow=shadow, glow=glow, bevel=bevel, extrude=extrude,
            reflection=reflection, plate=plate, spacing=spacing, arc=arc, rotate=rotate, flip=flip,
            align=align, limit=limit,
        )
        self._elements.append(_WordArt(x=x, y=y, cw=width, band=band))

    def status(self, text: str, *, x: float, y: float, width: float, status: str = "draft", height: float = 24, size: float = 14) -> None:
        """diagram({status}): a dashed-outline pill — position is a new simplified formula, see render_status()."""
        self._elements.append(_Status(x=x, y=y, width=width, text=text, status=status, height=height, size=size))

    def people(
        self,
        *,
        total: int,
        count: int,
        count2: int = 0,
        x: float,
        y: float,
        width: float,
        cols: int,
        size: float = 24,
        gap: float = 4,
        align: str | None = None,
        side: dict | None = None,
        tone: Tone | None = "accent",
        tone2: Tone | None = "danger",
        rest: Tone | None = "muted",
        alt: str = "",
    ) -> None:
        """lib/people.ts's people(): a grid of person icons, the emphasized ones filled. The
        layout formula (layout_people) IS byte-identical to Node (golden-tested live); only the
        `side` label's text width uses this port's approximation."""
        self._elements.append(_People(x=x, y=y, cw=width, cols=cols, size=size, gap=gap, total=total, count=count, count2=count2, align=align, side=side, tone=tone, tone2=tone2, rest=rest, alt=alt))

    def dots(
        self,
        dots: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        min: float = 0,
        max: float = 100,
        r: float = 5,
        zones: list[dict] | None = None,
        low_label: str | None = None,
        high_label: str | None = None,
        height: float | None = None,
        alt: str = "",
    ) -> None:
        """lib/people.ts's dots(): a lane with piled dots. `dots`: [{at, tone?}]. The pile-
        packing/zone formula (layout_dots) IS byte-identical to Node (golden-tested live); only
        label text widths use this port's approximation."""
        self._elements.append(_Dots(x=x, y=y, cw=width, r=r, dots=dots, zones=zones or [], min_val=min, max_val=max, width=width, low_label=low_label, high_label=high_label, height=height, alt=alt))

    # ---- arrow()/connect() ------------------------------------------------------------

    def arrow(
        self,
        source: Box | str,
        target: Box | str,
        *,
        style: ArrowStyle = "end",
        line: LineStyle | None = None,
        tone: Tone | None = None,
        label: str | None = None,
        chip: bool = False,
        label_at: float = 0.5,
    ) -> Arrow:
        source_id = source.id if isinstance(source, Box) else source
        target_id = target.id if isinstance(target, Box) else target
        if not any(b.id == source_id for b in self.boxes):
            raise ValueError(f"arrow(): unknown source id {source_id!r}")
        if not any(b.id == target_id for b in self.boxes):
            raise ValueError(f"arrow(): unknown target id {target_id!r}")
        a = Arrow(source=source_id, target=target_id, arrow=style, line=line, tone=tone, label=label, chip=chip, label_at=label_at)
        self.arrows.append(a)
        return a

    # ---- row() / grid() ----------------------------------------------------------------

    def row(
        self,
        children: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        height: float,
        gap: float = 16,
        justify: str | None = None,
        cols: int | None = None,
        item_width: float | None = None,
        arrows: bool = False,
    ) -> list[Box]:
        """lib/dsl/containers.ts's row(): equal/flex/fixed-width distribution — ported byte-identically
        from lib/layout-util.ts's rowChildGeometry() (pure arithmetic, no text metrics). Creates one
        Box per child at the computed x; `arrows=True` adds a connector between each adjacent pair
        (Node's renderRow() arrow style)."""
        band = {"gap": gap, "justify": justify, "cols": cols, "itemWidth": item_width, "children": children}
        geom = row_child_geometry(band, width)
        boxes = []
        for child, w, x_off in zip(children, geom["widths"], geom["xOffsets"]):
            kwargs = {k: v for k, v in child.items() if k not in ("label", "width", "flex", "span", "col")}
            boxes.append(self.box(child.get("label", ""), x=x + x_off, y=y, width=w, height=height, **kwargs))
        if arrows:
            for a, b in zip(boxes, boxes[1:]):
                self.arrow(a, b)
        return boxes

    def grid(self, children: list[dict], *, x: float, y: float, width: float, row_height: float, cols: int, gap: float = 16, row_gap: float | None = None) -> list[Box]:
        """lib/dsl/containers.ts's grid(): an N-column grid, each child in the next free cell, wrapping
        to a new row. Width distribution is lib/layout-util.ts's gridChildGeometry() (byte-identical)."""
        band = {"cols": cols, "gap": gap}
        geom = grid_child_geometry(band, width)
        rg = row_gap if row_gap is not None else gap
        boxes = []
        for i, child in enumerate(children):
            col, r = i % cols, i // cols
            kwargs = {k: v for k, v in child.items() if k not in ("label",)}
            boxes.append(self.box(child.get("label", ""), x=x + geom["xs"][col], y=y + r * (row_height + rg), width=geom["ws"][col], height=row_height, **kwargs))
        return boxes

    # ---- rendering -----------------------------------------------------------------------

    def _box_by_id(self, box_id: str) -> Box:
        for b in self.boxes:
            if b.id == box_id:
                return b
        raise KeyError(box_id)

    def _render_box(self, b: Box) -> str:
        # Mirrors Node's renderBox() concatenation exactly — it is NOT a uniform join: frame
        # carries its own trailing "\n  ", badge/tag need a caller-added LEADING "\n  ", and
        # stamp already carries its own leading "\n  " (lib/emit-boxes.ts:89-95).
        out = ""
        if b.frame:
            out += render_box_rect(x=b.x, y=b.y, w=b.width, h=b.height, tone=b.tone, dashed=b.dashed, dim=b.dim, fill=b.fill, stroke=b.stroke) + "\n  "
        if b.lines:
            # the title run has no color override of its own, so this is Node's runColorOf(tones, undefined, b.tone, day):
            # white on a solid/solid-danger box, plain text color otherwise (tokens.ts:220-222)
            fill_color = run_color_of(None, b.tone, day=1)
            # Node only indents the FIRST (title) line for a step badge; this port has no
            # title/body distinction, so — as a documented simplification — every line shifts.
            indent = STEP_INDENT if b.step is not None else 0
            out += text_lines(b.lines, x=b.x + BOX_PAD_X + indent, top=b.y + BOX_PAD_Y, size=ROLES["title"], weight=700, fill=fill_color)
        if b.step is not None:
            title_baseline_y = b.y + BOX_PAD_Y + ROLES["title"]
            out += "\n  " + render_step_badge(x=b.x, pad_x=BOX_PAD_X, title_baseline_y=title_baseline_y, step=b.step, tone=b.tone, dim=b.dim)
        if b.tag is not None:
            tag_w = approx_width_of(b.tag, 14, 700) + 2 * TAG_PAD_X
            tx = b.x + 8 + (b.width - 16 - tag_w) * b.tag_at
            tag_box = {"x": tx, "y": b.y - TAG_H / 2, "w": tag_w, "h": TAG_H}
            out += "\n  " + render_tag(tag_box=tag_box, tag=b.tag, tag_tone=b.tag_tone, tone=b.tone, dim=b.dim)
        if b.stamp is not None:
            stamp_w = approx_width_of(b.stamp, ROLES["note"], 400) + 2 * STAMP_PAD_X
            out += render_stamp(x=b.x, y=b.y, w=b.width, h=b.height, stamp=b.stamp, stamp_w=stamp_w, note_size=ROLES["note"])
        return out

    def _render_element(self, el: object) -> str:
        if isinstance(el, Box):
            return self._render_box(el)
        if isinstance(el, _Caption):
            return render_caption(x=el.x, y=el.y, w=el.w, text=el.text, size=ROLES["title"], align=el.align, tone=el.tone)
        if isinstance(el, _Group):
            # lib/emit-boxes.ts:98-101 renderGroup(): rect and stamp concatenate directly
            # (renderStamp already carries its own leading "\n  "); the title caption is a
            # SEPARATE top-level band in Node (lib/layout-util.ts's groupTitleBand()), so it
            # joins here the same way two bands join in the body list ("\n\n  ").
            out = render_group_rect(x=el.x, y=el.y, w=el.w, h=el.h, tone=el.tone, dashed=el.dashed, dim=el.dim)
            if el.stamp:
                stamp_w = approx_width_of(el.stamp, ROLES["note"], 400) + 2 * STAMP_PAD_X
                out += render_stamp(x=el.x, y=el.y, w=el.w, h=el.h, stamp=el.stamp, stamp_w=stamp_w, note_size=ROLES["note"])
            if el.title:
                title_color = text_color_of("accent" if el.tone == "accent" else None, 1)
                title_svg = text_lines([el.title], x=el.x + BOX_PAD_X, top=el.y + BOX_PAD_Y, size=ROLES["title"], weight=700, fill=title_color)
                out += "\n\n  " + title_svg
            return out
        if isinstance(el, _Banner):
            return render_banner(x=el.x, y=el.y, w=el.w, h=el.h, lines=el.lines, size=ROLES["title"], tone=el.tone)
        if isinstance(el, _Legend):
            return "\n  ".join(render_legend_item(note_size=ROLES["note"], **item) for item in el.items)
        if isinstance(el, _Raw):
            return render_raw(x=el.x, y=el.y, w=el.w, h=el.h, day=1, draw=el.draw)
        if isinstance(el, _Pyramid):
            return self._render_pyramid(el)
        if isinstance(el, _Curve):
            from .figures import curve_points

            axis_label_w, axis_bottom_gap, top_pad, right_pad = 44, 28, 14, 8
            axis_x = el.x + axis_label_w
            axis_right = el.x + el.width - right_pad
            axis_top = el.y + top_pad
            axis_bottom = el.y + el.height - axis_bottom_gap
            points = curve_points(raw_points=el.points, axis_x=axis_x, axis_right=axis_right, axis_top=axis_top, axis_bottom=axis_bottom)
            return render_curve(axis_x=axis_x, axis_right=axis_right, axis_top=axis_top, axis_bottom=axis_bottom, points=points, day=el.day, y_top_label=el.y_top_label, y_bottom_label=el.y_bottom_label, x_label=el.x_label)
        if isinstance(el, _Status):
            text_y = el.y + el.height / 2 + el.size * 0.38
            return render_status(x=el.x, y=el.y, w=el.width, h=el.height, text_y=text_y, text=el.text, status=el.status, size=el.size)
        if isinstance(el, _People):
            laid = layout_people(cols=el.cols, size=el.size, gap=el.gap, total=el.total, count=el.count, count2=el.count2, x=el.x, y=el.y, cw=el.cw, width_of=approx_width_of, align=el.align, side=el.side, roles=ROLES)
            return render_people(x=laid["x"], y=laid["y"], size=laid["size"], icons=laid["icons"], texts=laid["texts"], tone=el.tone, tone2=el.tone2, rest=el.rest, alt=el.alt, day=el.day)
        if isinstance(el, _Dots):
            laid = layout_dots(r=el.r, dots=el.dots, zones=el.zones, min_val=el.min_val, max_val=el.max_val, x=el.x, y=el.y, cw=el.cw, width_of=approx_width_of, width=el.width, low_label=el.low_label, high_label=el.high_label, height=el.height, roles=ROLES)
            return render_dots(axis=laid["axis"], zones=laid["zones"], dots=laid["dots"], texts=laid["texts"], r=el.r, alt=el.alt, day=el.day)
        if isinstance(el, _Timeline):
            laid = layout_timeline(now=el.now, deadline=el.deadline, marks=el.marks, from_=el.from_, to=el.to, span=el.span, remaining=el.remaining, x=el.x, y=el.y, w=el.w, width_of=approx_width_of, roles=ROLES)
            return render_timeline(laid, day=el.day)
        if isinstance(el, _Gantt):
            laid = layout_gantt(rows=el.rows, x=el.x, y=el.y, w=el.w, width_of=approx_width_of, roles=ROLES, from_=el.from_, to=el.to, today=el.today, today_label=el.today_label, extend_to_today=el.extend_to_today)
            return render_gantt(laid, day=el.day)
        if isinstance(el, _Cloud):
            laid = layout_cloud_band(boxes=el.boxes, x=el.x, y=el.y, w=el.w, width_of=approx_width_of, roles=ROLES, max_node_w=el.max_node_w, assumptions=el.assumptions, conflict_label=el.conflict_label)
            return render_cloud(laid, day=el.day)
        if isinstance(el, _Tree):
            laid = layout_tree_band(el.root, el.x, el.y, el.w, approx_width_of, ROLES, dir_opt=el.dir_opt, max_node_w=el.max_node_w, balanced=el.balanced, layout_mode=el.layout_mode, sides=el.sides, edges_opt=el.edges_opt)
            return render_tree(laid, day=el.day)
        if isinstance(el, _Table):
            laid = layout_table(columns=el.columns, rows=el.rows, x=el.x, y=el.y, w=el.w, width_of=approx_width_of, roles=ROLES, width=el.width, title=el.title, dense=el.dense, header=el.header, row_header=el.row_header, header_h=el.header_h, cell_h=el.cell_h, row_curve=el.row_curve)
            return render_table(laid, day=el.day, roles=ROLES)
        if isinstance(el, _Sequence):
            laid = layout_sequence(actors=el.actors, steps=el.steps, x=el.x, y=el.y, w=el.w, width_of=approx_width_of, roles=ROLES, numbered=el.numbered)
            return render_sequence(laid, day=el.day, roles=ROLES)
        if isinstance(el, _FlowShape):
            laid = layout_flow_shape(el.band, el.x, el.y, el.cw, approx_width_of, ROLES, "phrase")
            return render_flow_shape(laid, day=el.day)
        if isinstance(el, _WordArt):
            laid = layout_word_art(el.band, el.x, el.y, el.cw, approx_width_of, ROLES, "phrase")
            return render_word_art(laid, day=el.day)
        raise TypeError(f"unknown element type {type(el)!r}")

    def _render_pyramid(self, el: _Pyramid) -> str:
        n = len(el.layers)
        base_width = el.width if el.width is not None else self.width
        total_h = n * el.layer_height
        cx = el.x + base_width / 2
        day = el.day
        laid_layers = []
        for i in range(n):
            geom = pyramid_layer_geometry(n=n, i=i, base_width=base_width, apex_ratio=el.apex_ratio, layer_height=el.layer_height, cx=cx, stack_bottom_y=el.y + total_h)
            bg_lum = blend_luminance(PALETTE["bg"], PALETTE[day]["accent"], geom["opacity"])
            text_color = best_text_color(bg_lum)
            top_w = geom["topW"]
            wrap_width = max(40, top_w - 24)
            lines = wrap_text(el.layers[i], max_width=wrap_width, atom_width=lambda a: approx_width_of(a, ROLES["title"], 700), mode="phrase")
            mid_y = (geom["topY"] + geom["bottomY"]) / 2
            line_gap = ROLES["title"] * LH_EM
            text_ys = [js_round(mid_y + (li - (len(lines) - 1) / 2) * line_gap + ROLES["title"] * 0.35) for li in range(len(lines))]
            laid_layers.append({"points": geom["points"], "opacity": geom["opacity"], "textColor": text_color, "lines": lines, "textYs": text_ys, "cx": cx})
        return render_pyramid(laid_layers, day=day, title_size=ROLES["title"])

    def _route(self, a: Arrow) -> list[dict]:
        source, target = self._box_by_id(a.source), self._box_by_id(a.target)
        sx, sy = source.x + source.width / 2, source.y + source.height / 2
        tx, ty = target.x + target.width / 2, target.y + target.height / 2
        # pick the source/target box edge nearest the straight line between their centers
        from_side = "right" if tx >= sx else "left"
        to_side = "left" if tx >= sx else "right"
        if abs(ty - sy) > abs(tx - sx):
            from_side = "bottom" if ty >= sy else "top"
            to_side = "top" if ty >= sy else "bottom"
        return [_edge_point(source, from_side), _edge_point(target, to_side)]

    def render_svg(self) -> str:
        """Builds the final SVG document — see module docstring for the non-ported/ported split."""
        body = "\n\n  ".join(self._render_element(el) for el in self._elements)
        connects = [render_connect(points=self._route(a), arrow=a.arrow, line=a.line, tone=a.tone, label=a.label, chip=a.chip, label_at=a.label_at) for a in self.arrows]
        connect_svg = "\n\n  ".join(connects)
        has_arrow = any(a.arrow != "none" for a in self.arrows)
        return emit_svg(width=self.width, height=self.height, body=body, connect_svg=connect_svg, has_arrow=has_arrow)

    def save(self, path: str) -> None:
        """spec section 4: `.save()` picks the format from the extension — `.svg` or `.html`."""
        from .render_html import render_html

        svg = self.render_svg()
        if path.endswith(".html"):
            content = render_html(svg, download_name=path.rsplit("/", 1)[-1].removesuffix(".html") + ".svg")
        elif path.endswith(".svg"):
            content = svg
        else:
            raise ValueError(f"save(): path must end in .svg or .html (got {path!r})")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
