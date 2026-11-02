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
from .bars import bars_band, layout_bars, render_bars
from .charts import layout_chart, render_chart
from .heatmap import heatmap_band
from .radar import radar_band
from .sankey import sankey_band
from .butterfly import butterfly_band
from .bubble import bubble_band
from .combo import combo_band
from .catplot import cat_band
from .distplot import dist_band
from .multiplot import multi_band
from .regplot import reg_band
from .clustermap import cluster_band
from .lines import burndown_band, burnup_band, lines_band, strategy_canvas_band
from .plane import layout_plane, plane_band, render_plane
from .harvey import harvey_band
from .stacked import mekko_band, stacked_bars_band
from .tornado import tornado_band
from .treemap import treemap_band
from .waterfall import waterfall_band
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
class _Bars:
    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1


@dataclass
class _Chart:
    """Generic wrapper for every chart kind (heatmap, and whatever is ported next) — they all
    share one layout_chart()/render_chart() dispatcher (lib/charts.ts/lib/charts-emit.ts)."""

    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1


@dataclass
class _Plane:
    """plane() is a standalone band type ("plane"), not part of the "chart" family — its own
    layout_plane()/render_plane() pair (lib/plane.ts/lib/emit-figures.ts's renderPlane())."""

    x: float
    y: float
    w: float
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

    def bars(
        self,
        data: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        unit: str | None = None,
        direction: str | None = None,
        stack: bool = False,
        height: float | None = None,
        id: str | None = None,
        max_value: float | None = None,
        plot_inset: tuple[float, float] | None = None,
        labels: str | None = None,
        axis: bool | None = None,
        grid: bool | None = None,
        baseline: bool | None = None,
        bar_ratio: float | None = None,
        label_role: str | None = None,
        hide_zero: bool = False,
        lines: list[dict] | None = None,
        vlines: list[dict] | None = None,
        curve: dict | None = None,
        cumulative: dict | None = None,
        edges: list[str] | None = None,
        value_format=None,
    ) -> None:
        """lib/dsl/bars.ts's bars(): horizontal or vertical bars (`direction`: 'h'/'v'), plain
        or `stack`ed, with an optional cumulative/Pareto overlay, reference lines and edge
        labels. `data`: [{label, value | range, id?, tone?, series?, replaces?}]. The layout
        formula IS byte-identical to Node (golden-tested live); only text widths use this
        port's approximation. rangeBars()/pareto()/histogram()/scatter() convenience wrappers
        are not supported — build their equivalent `data`/opts directly."""
        band = bars_band(
            data, unit=unit, direction=direction, stack=stack, height=height, id=id, max_value=max_value,
            plot_inset=plot_inset, labels=labels, axis=axis, grid=grid, baseline=baseline, bar_ratio=bar_ratio,
            label_role=label_role, hide_zero=hide_zero, lines=lines, vlines=vlines, curve=curve,
            cumulative=cumulative, edges=edges, value_format=value_format,
        )
        self._elements.append(_Bars(x=x, y=y, w=width, band=band))

    def heatmap(
        self,
        rows: list[str],
        cols: list[str],
        values: list[list[float | None]],
        *,
        x: float,
        y: float,
        width: float,
        unit: str | None = None,
        decimals: int | None = None,
        min: float | None = None,
        max: float | None = None,
        levels: int | None = None,
        row_header: bool | None = None,
        corner: str | None = None,
        scale: bool | None = None,
        cell_h: float | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's heatmap(): a table of numbers shaded by size (a cohort table, a
        retention table). `values[i][j]` may be `None` for an empty cell. The layout formula
        IS byte-identical to Node (golden-tested live); only text widths use this port's
        approximation."""
        opts: dict = {}
        for k, v in (
            ("unit", unit), ("decimals", decimals), ("min", min), ("max", max), ("levels", levels),
            ("rowHeader", row_header), ("corner", corner), ("scale", scale), ("cellH", cell_h),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = heatmap_band(rows, cols, values, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def sankey(
        self,
        nodes: list,
        links: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        unit: str | None = None,
        align: str | None = None,
        link_labels: bool | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's sankey(): flows between layers of nodes. `nodes`: a label string
        or {id, label?, tone?}. `links`: [{from, to, value, tone?}]. The layout formula IS
        byte-identical to Node (golden-tested live); only text widths use this port's
        approximation. Node icons (`SankeyNode.icon`) are not supported."""
        opts: dict = {}
        for k, v in (
            ("unit", unit), ("align", align), ("linkLabels", link_labels),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = sankey_band(nodes, links, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def radar(
        self,
        axes: list[str],
        series: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        min: float | None = None,
        max: float | None = None,
        rings: int | None = None,
        values: bool | None = None,
        unit: str | None = None,
        fill: bool | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's radar(): 3-12 axes, 1-4 series (each told apart by line style AND
        marker shape, never colour alone). `series`: [{label, values: [...], id?}]. The layout
        formula IS byte-identical to Node (golden-tested live); only text widths use this
        port's approximation."""
        opts: dict = {}
        for k, v in (
            ("min", min), ("max", max), ("rings", rings), ("values", values), ("unit", unit), ("fill", fill),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = radar_band(axes, series, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def treemap(
        self,
        tree,
        *,
        x: float,
        y: float,
        width: float,
        unit: str | None = None,
        percent: bool | None = None,
        strict: bool | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's treemap(): a tree of values as nested rectangles (squarified),
        area proportional to value. `tree`: one node or a list of root nodes, each
        {label, value | children: [...], id?, tone?}. The layout formula IS byte-identical to
        Node (golden-tested live); only text widths use this port's approximation."""
        opts: dict = {}
        for k, v in (
            ("unit", unit), ("percent", percent), ("strict", strict),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = treemap_band(tree, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def waterfall(
        self,
        steps: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        unit: str | None = None,
        axis: bool | None = None,
        connectors: bool | None = None,
        direction: str | None = None,
        domain: tuple[float, float] | None = None,
        plot_inset: tuple[float, float] | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's waterfall(): how a start value turns into an end value, step by
        step. `steps`: [{label, value?, kind?: 'start'|'delta'|'subtotal'|'total', id?, tone?}]
        (the first step defaults to 'start', every other to 'delta'). `direction` is Node's
        `dir` ('v' default, or 'h'). The layout formula IS byte-identical to Node
        (golden-tested live); only text widths use this port's approximation."""
        opts: dict = {}
        for k, v in (
            ("unit", unit), ("axis", axis), ("connectors", connectors), ("dir", direction), ("domain", domain),
            ("plotInset", plot_inset), ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = waterfall_band(steps, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def stacked_bars(
        self,
        columns: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        unit: str | None = None,
        percent: bool | None = None,
        domain: tuple[float, float] | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's stackedBars(): columns cut into segments. `columns`:
        [{label, parts: [{label, value}, ...], id?}]. `percent: true` makes 100% columns. The
        layout formula IS byte-identical to Node (golden-tested live); only text widths use
        this port's approximation."""
        opts: dict = {}
        for k, v in (
            ("unit", unit), ("percent", percent), ("domain", domain),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = stacked_bars_band(columns, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def mekko(
        self,
        columns: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        unit: str | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's mekko(): a column's width is its total, a segment's height its
        share of the column (so area = share of the whole). `columns`:
        [{label, parts: [{label, value}, ...], id?}]. The layout formula IS byte-identical to
        Node (golden-tested live); only text widths use this port's approximation."""
        opts: dict = {}
        for k, v in (("unit", unit), ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width)):
            if v is not None:
                opts[k] = v
        band = mekko_band(columns, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def tornado(
        self,
        items: list[dict],
        *,
        base: float,
        x: float,
        y: float,
        width: float,
        unit: str | None = None,
        low_label: str | None = None,
        high_label: str | None = None,
        base_label: str | None = None,
        sort: bool | None = None,
        low_tone: str | None = None,
        high_tone: str | None = None,
        domain: tuple[float, float] | None = None,
        plot_inset: tuple[float, float] | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's tornado(): a sensitivity chart — each row's low/high bars run
        from the base result. `items`: [{label, low, high, id?}]. The layout formula IS
        byte-identical to Node (golden-tested live); only text widths use this port's
        approximation."""
        opts: dict = {"base": base}
        for k, v in (
            ("unit", unit), ("lowLabel", low_label), ("highLabel", high_label), ("baseLabel", base_label),
            ("sort", sort), ("lowTone", low_tone), ("highTone", high_tone), ("domain", domain), ("plotInset", plot_inset),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = tornado_band(items, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def butterfly(
        self,
        rows: list[dict],
        *,
        left_label: str,
        right_label: str,
        x: float,
        y: float,
        width: float,
        unit: str | None = None,
        sort: str | None = None,
        left_tone: str | None = None,
        right_tone: str | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's butterfly(): a two-sided bar chart — each row's two bars grow
        outwards from a column of names in the middle. `rows`: [{label, left, right, id?}].
        The layout formula IS byte-identical to Node (golden-tested live); only text widths
        use this port's approximation."""
        opts: dict = {"leftLabel": left_label, "rightLabel": right_label}
        for k, v in (
            ("unit", unit), ("sort", sort), ("leftTone", left_tone), ("rightTone", right_tone),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = butterfly_band(rows, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def harvey(
        self,
        rows: list,
        cols: list[str],
        values: list[list[float | None]],
        *,
        x: float,
        y: float,
        width: float,
        levels: tuple[str, str, str, str, str] | None = None,
        corner: str | None = None,
        highlight: list[str] | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's harvey(): a table of Harvey balls, each a circle filled by a
        quarter/half/three-quarters/fully. `rows`: a label string or {label, id?}. `values`:
        0-4 (quarters filled) or None (not rated). The layout formula IS byte-identical to
        Node (golden-tested live); only text widths use this port's approximation."""
        opts: dict = {}
        for k, v in (
            ("levels", levels), ("corner", corner), ("highlight", highlight),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = harvey_band(rows, cols, values, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def bubble(
        self,
        points: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        x_axis: dict | None = None,
        y_axis: dict | None = None,
        size_title: str | None = None,
        size_unit: str | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's bubble(): a scatter chart whose third measure is the bubble's
        AREA. `points`: [{label, x, y, size, tone?, id?}]. `x_axis`/`y_axis` are Node's
        `x`/`y` ({title?, unit?, min?, max?, line?, lineLabel?}) — renamed here since `x`/`y`
        are this method's own position kwargs. The layout formula IS byte-identical to Node
        (golden-tested live, including the axis auto-widening loop); only text widths use
        this port's approximation."""
        opts: dict = {}
        for k, v in (
            ("x", x_axis), ("y", y_axis), ("sizeTitle", size_title), ("sizeUnit", size_unit),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = bubble_band(points, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def combo(
        self,
        categories: list[str],
        series: list[dict],
        *,
        x: float,
        y: float,
        width: float,
        y_axis: dict | None = None,
        y2_axis: dict | None = None,
        values: bool | None = None,
        stack: bool | None = None,
        id: str | None = None,
        height: float | None = None,
        label_role: str | None = None,
        alt: str | None = None,
    ) -> None:
        """lib/dsl/charts.ts's combo(): bars and lines over the same categories. `series`:
        [{label, type: 'bar'|'line', values: [...], axis?: 'left'|'right', tone?, id?}] (a
        bar is always on the left axis; a line defaults to the right when any bar is
        present). `y_axis`/`y2_axis` are Node's `y`/`y2` ({min?, max?, unit?, title?}),
        renamed here since `y` is this method's own position kwarg. `stack: true` piles the
        bar series into one column per category. The layout formula IS byte-identical to
        Node (golden-tested live); only text widths use this port's approximation."""
        opts: dict = {}
        for k, v in (
            ("y", y_axis), ("y2", y2_axis), ("values", values), ("stack", stack),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        ):
            if v is not None:
                opts[k] = v
        band = combo_band(categories, series, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def catplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """lib/dsl/charts-stats.ts's catplot(): seaborn's categorical plots from raw values —
        boxplot/violinplot/stripplot/swarmplot/pointplot/barplot, one or several layers
        (`opts.kind`, a kind or a list of kinds drawn in order). `data`: a list of
        {label, values} / {label, hues: [{name, values}]} groups, or {label: values, ...}.
        `opts` is Node's own nested CatOpts, passed through as-is (kind?, dir?, label?,
        unit?, error?, values?, counts?, scale?, id?, width?, height?, labelRole?). The
        statistics (quartiles, KDE, confidence interval, beeswarm — lib/stats.ts) and the
        layout formula ARE byte-identical to Node (golden-tested live); only text widths use
        this port's approximation."""
        band = cat_band("catplot", data, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def boxplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn boxplot(): quartiles, whiskers at 1.5 IQR, outliers as rings. See
        catplot() for `data`/`opts` (kind is fixed to 'box')."""
        band = cat_band("boxplot", data, opts, kind="box")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def violinplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn violinplot(): a kernel density estimate mirrored around each group, with
        its quartiles inside. See catplot() for `data`/`opts` (kind is fixed to 'violin')."""
        band = cat_band("violinplot", data, opts, kind="violin")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def stripplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn stripplot(): every value as a point, spread sideways without a pattern.
        See catplot() for `data`/`opts` (kind is fixed to 'strip')."""
        band = cat_band("stripplot", data, opts, kind="strip")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def swarmplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn swarmplot(): every value as a point, laid out so that none touch. See
        catplot() for `data`/`opts` (kind is fixed to 'swarm')."""
        band = cat_band("swarmplot", data, opts, kind="swarm")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def pointplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn pointplot(): the mean of each group with its error bar, joined by a line
        per hue. See catplot() for `data`/`opts` (kind is fixed to 'point')."""
        band = cat_band("pointplot", data, opts, kind="point")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def barplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn barplot(): the mean of each group as a bar from 0, with its error bar.
        See catplot() for `data`/`opts` (kind is fixed to 'bar')."""
        band = cat_band("barplot", data, opts, kind="bar")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def displot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """lib/dsl/charts-stats.ts's displot(): seaborn's distribution plots from raw values —
        histplot/kdeplot/ecdfplot/rugplot, one or several layers (`opts.kind`). `data`: a
        list of numbers, a list of {label, values} groups (up to 4), or {label: values, ...}.
        `opts` is Node's own nested DistOpts, passed through as-is (kind?, label?, unit?,
        stat?, bins?, binWidth?, element?, bw?, xRange?, yRange?, id?, width?, height?,
        labelRole?). The bins/KDE/ECDF math (lib/stats.ts, lib/qc.ts) and the layout formula
        ARE byte-identical to Node (golden-tested live); only text widths use this port's
        approximation."""
        band = dist_band("displot", data, opts, "hist")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def histplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn histplot(): round class widths shared by the groups. See displot() for
        `data`/`opts` (kind is fixed to 'hist')."""
        band = dist_band("histplot", data, opts, "hist")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def kdeplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn kdeplot(): a Gaussian KDE with Scott's bandwidth, filled under the curve.
        See displot() for `data`/`opts` (kind is fixed to 'kde')."""
        band = dist_band("kdeplot", data, opts, "kde")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def ecdfplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn ecdfplot(): the share of values at or below x, as a step line. See
        displot() for `data`/`opts` (kind is fixed to 'ecdf')."""
        band = dist_band("ecdfplot", data, opts, "ecdf")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def rugplot(self, data, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn rugplot(): a tick for every value. See displot() for `data`/`opts` (kind
        is fixed to 'rug')."""
        band = dist_band("rugplot", data, opts, "rug")
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def hist2d(self, data: dict, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn histplot(x=, y=): a 2-D histogram — points counted in round-sized cells,
        each cell shaded and labelled. `data`: {x: [...], y: [...]}. `opts` is Node's own
        nested MultiOpts, passed through as-is (xLabel?, yLabel?, bins?, id?, width?,
        height?, labelRole?). The binning math (lib/stats.ts) and the layout formula ARE
        byte-identical to Node (golden-tested live); only text widths use this port's
        approximation."""
        band = multi_band("hist2d", "hist2d", data, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def jointplot(self, data: dict, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn jointplot(): a scatter with the histogram of each variable beside it.
        `data`: {x: [...], y: [...], group?: [...]} (group tells points apart by marker
        shape, up to 4). See hist2d() for `opts`."""
        band = multi_band("jointplot", "joint", data, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def kde2d(self, data: dict, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn kdeplot(x=, y=): a Gaussian density over the plane as filled bands with
        contour lines. `data`: {x: [...], y: [...]}. See hist2d() for `opts`."""
        band = multi_band("kde2d", "kde2d", data, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def pairplot(self, data: dict, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn pairplot(): every pair of 2 to 6 variables as a scatter, each variable's
        histogram on the diagonal. `data`: {varName: [...], ...}. `opts` adds `corner?`
        (lower triangle + diagonal only) and `groups?` on top of hist2d()'s own opts."""
        band = multi_band("pairplot", "pair", data, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def regplot(self, data: dict, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn regplot()/lmplot(): the points, the least-squares line (`order: 2 | 3` for
        a curve) and its 95% confidence band, one fit per group. `data`: {x: [...], y: [...],
        group?: [...]} (up to 4 groups). `opts` is Node's own nested RegOpts, passed through
        as-is (xLabel?, yLabel?, order?, band?, stats?, lowess?, frac?, groups?, xRange?,
        yRange?, id?, width?, height?, labelRole?). The fit math (lib/stats.ts's polyFit/
        lowessFit) and the layout formula ARE byte-identical to Node (golden-tested live);
        only text widths use this port's approximation."""
        band = reg_band("regplot", False, data, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def residplot(self, data: dict, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn residplot(): the residuals around the same fit, with the zero line. See
        regplot() for `data`/`opts`."""
        band = reg_band("residplot", True, data, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def clustermap(self, rows: list[str], cols: list[str], values: list[list[float]], *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """seaborn clustermap(): a heatmap whose rows and columns are put in the order of a
        hierarchical clustering (average linkage), with the two dendrograms beside it.
        `opts` is Node's own nested ClusterOpts, passed through as-is (unit?, rows?, cols?
        (cluster each axis, default true for both), scale? ('row' | 'col', scale before
        clustering/shading), values? (write the numbers, default true), id?, width?,
        height?, labelRole?). The clustering math (lib/stats.ts's averageLinkage/
        dendrogramOrder, deterministic) and the layout formula ARE byte-identical to Node
        (golden-tested live); only text widths use this port's approximation."""
        band = cluster_band(rows, cols, values, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def plane(self, opts: dict, *, x: float, y: float, width: float) -> None:
        """lib/dsl/figures.ts's plane(): a coordinate plane — axes with ticks, points, guide
        lines, dimension lines and labels, all in the plane's own units. Unlike the other
        band methods, `opts` is passed through as Node's own nested shape (not exploded into
        keyword arguments — plane() has too many deeply-nested optional structures for that
        to be practical): {x: {label?, max, min?, step?, ticks?, categories?}, y: {...},
        yDown?, stages?, points?: [{id?, at: [x,y], label?, labelAt?, tone?, shape?,
        evolves?: {to}}], lines?: [{from, to, tone?, dashed?, arrow?}],
        dims?: [{from, to, label, side?, tone?}], paths?: [{through, smooth?, arrow?,
        tone?, dashed?}], labels?: [{at, text, anchor?, tone?, bold?}], grid?, endLabels?,
        height?, width?, labelRole?, id?}. A position ([x, y]) may be a point's id. The
        layout formula IS byte-identical to Node (golden-tested live, including monotone
        and centripetal curve fitting for smooth paths); only text widths use this port's
        approximation."""
        band = plane_band(opts)
        self._elements.append(_Plane(x=x, y=y, w=width, band=band))

    def lines(self, series: list[dict], *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """lib/dsl/charts.ts's lines(): a multi-series line chart worked out into a plane()
        (categories or numbers on x, a marker shape and line style per series, named at the
        end of its line; `ideal: true` draws a dashed/muted/markerless plan line).
        `series`: [{label, values: [...] (one per category, null for a gap) | [[x,y],...],
        ideal?, smooth?}]. `opts` (Node's own nested LinesOpts, passed through as-is):
        {x?: {categories? | min/max/step/ticks, label?}, y?: {...}, target?: {at, label?},
        annotate?, markers?, endLabels?, grid?, height?, width?, labelRole?, id?}. The
        layout formula IS byte-identical to Node (golden-tested live); only text widths use
        this port's approximation."""
        band = lines_band(series, opts)
        self._elements.append(_Plane(x=x, y=y, w=width, band=band))

    def burndown(self, spec: dict, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """lib/dsl/charts.ts's burndown(): the work left against the days, with the ideal
        straight line from the total to 0. `spec`: {total, days, actual: [...] (one per day
        from day 0, null for days not yet reached)}. `opts` is lines()'s own LinesOpts,
        passed through as-is. The layout formula IS byte-identical to Node (golden-tested
        live); only text widths use this port's approximation."""
        band = burndown_band(spec, opts)
        self._elements.append(_Plane(x=x, y=y, w=width, band=band))

    def burnup(self, spec: dict, *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """lib/dsl/charts.ts's burnup(): the work done climbing towards the scope line
        (which may move). `spec`: {scope: number | [number, ...] (one per day, may grow),
        days, done: [...] (one per day from day 0, null for days not yet reached)}. `opts`
        is lines()'s own LinesOpts, passed through as-is. The layout formula IS
        byte-identical to Node (golden-tested live); only text widths use this port's
        approximation."""
        band = burnup_band(spec, opts)
        self._elements.append(_Plane(x=x, y=y, w=width, band=band))

    def strategy_canvas(self, factors: list[str], series: list[dict], *, x: float, y: float, width: float, opts: dict | None = None) -> None:
        """lib/dsl/charts.ts's strategyCanvas(): factors of competition on x, the level
        offered (low to high) on y, one line per company. `series`: [{label, values: [one
        level per factor]}]. `opts` adds `levels?: {min?, max?, low?, high?}` on top of
        lines()'s own LinesOpts. The layout formula IS byte-identical to Node
        (golden-tested live); only text widths use this port's approximation."""
        band = strategy_canvas_band(factors, series, opts)
        self._elements.append(_Plane(x=x, y=y, w=width, band=band))

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
        if isinstance(el, _Bars):
            laid = layout_bars(el.band, el.x, el.y, el.w, approx_width_of, ROLES)
            return render_bars(laid, day=el.day)
        if isinstance(el, _Chart):
            laid = layout_chart(el.band, el.x, el.y, el.w, approx_width_of, ROLES, "phrase")
            return render_chart(laid, day=el.day)
        if isinstance(el, _Plane):
            laid = layout_plane(el.band, el.x, el.y, el.w, approx_width_of, ROLES)
            return render_plane(laid, day=el.day)
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
