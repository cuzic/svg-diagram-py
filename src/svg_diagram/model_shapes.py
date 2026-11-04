"""Diagram band methods for the "shapes" domain: pyramid/curve/timeline/gantt/cloud/
tree/mindmap/table/sequence/wordart/people/dots — each a standalone figure with its own
layout_X()/render_X() pair (ADR/lib references are in each method's own docstring, carried
over verbatim from model.py). Mixed into `Diagram` by model.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .approx_width import approx_width_of
from .cloud import layout_cloud_band, render_cloud
from .emit_common import LH_EM, js_round
from .figures import curve_points, pyramid_layer_geometry, render_curve, render_pyramid
from .gantt import layout_gantt, render_gantt
from .model_shared import Tone
from .people_dots import layout_dots, layout_people, render_dots, render_people
from .sequence import layout_sequence, render_sequence
from .table import layout_table, render_table
from .timeline import layout_timeline, render_timeline
from .tokens import PALETTE, ROLES, best_text_color, blend_luminance
from .tree import layout_tree_band, render_tree
from .wordart import layout_word_art, render_word_art, word_art_band
from .wrap import wrap_text


@dataclass
class _Pyramid:
    x: float
    y: float
    layers: list[str]
    width: float | None = None
    layer_height: float = 76
    apex_ratio: float = 0.3
    day: int | str = 1

    def render(self) -> str:
        n = len(self.layers)
        base_width = self.width
        total_h = n * self.layer_height
        cx = self.x + base_width / 2
        day = self.day
        laid_layers = []
        for i in range(n):
            geom = pyramid_layer_geometry(n=n, i=i, base_width=base_width, apex_ratio=self.apex_ratio, layer_height=self.layer_height, cx=cx, stack_bottom_y=self.y + total_h)
            bg_lum = blend_luminance(PALETTE["bg"], PALETTE[day]["accent"], geom["opacity"])
            text_color = best_text_color(bg_lum)
            top_w = geom["topW"]
            wrap_width = max(40, top_w - 24)
            lines = wrap_text(self.layers[i], max_width=wrap_width, atom_width=lambda a: approx_width_of(a, ROLES["title"], 700), mode="phrase")
            mid_y = (geom["topY"] + geom["bottomY"]) / 2
            line_gap = ROLES["title"] * LH_EM
            text_ys = [js_round(mid_y + (li - (len(lines) - 1) / 2) * line_gap + ROLES["title"] * 0.35) for li in range(len(lines))]
            laid_layers.append({"points": geom["points"], "opacity": geom["opacity"], "textColor": text_color, "lines": lines, "textYs": text_ys, "cx": cx})
        return render_pyramid(laid_layers, day=day, title_size=ROLES["title"])


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

    def render(self) -> str:
        axis_label_w, axis_bottom_gap, top_pad, right_pad = 44, 28, 14, 8
        axis_x = self.x + axis_label_w
        axis_right = self.x + self.width - right_pad
        axis_top = self.y + top_pad
        axis_bottom = self.y + self.height - axis_bottom_gap
        points = curve_points(raw_points=self.points, axis_x=axis_x, axis_right=axis_right, axis_top=axis_top, axis_bottom=axis_bottom)
        return render_curve(axis_x=axis_x, axis_right=axis_right, axis_top=axis_top, axis_bottom=axis_bottom, points=points, day=self.day, y_top_label=self.y_top_label, y_bottom_label=self.y_bottom_label, x_label=self.x_label)


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

    def render(self) -> str:
        laid = layout_people(cols=self.cols, size=self.size, gap=self.gap, total=self.total, count=self.count, count2=self.count2, x=self.x, y=self.y, cw=self.cw, width_of=approx_width_of, align=self.align, side=self.side, roles=ROLES)
        return render_people(x=laid["x"], y=laid["y"], size=laid["size"], icons=laid["icons"], texts=laid["texts"], tone=self.tone, tone2=self.tone2, rest=self.rest, alt=self.alt, day=self.day)


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

    def render(self) -> str:
        laid = layout_dots(r=self.r, dots=self.dots, zones=self.zones, min_val=self.min_val, max_val=self.max_val, x=self.x, y=self.y, cw=self.cw, width_of=approx_width_of, width=self.width, low_label=self.low_label, high_label=self.high_label, height=self.height, roles=ROLES)
        return render_dots(axis=laid["axis"], zones=laid["zones"], dots=laid["dots"], texts=laid["texts"], r=self.r, alt=self.alt, day=self.day)


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

    def render(self) -> str:
        laid = layout_timeline(now=self.now, deadline=self.deadline, marks=self.marks, from_=self.from_, to=self.to, span=self.span, remaining=self.remaining, x=self.x, y=self.y, w=self.w, width_of=approx_width_of, roles=ROLES)
        return render_timeline(laid, day=self.day)


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

    def render(self) -> str:
        laid = layout_gantt(rows=self.rows, x=self.x, y=self.y, w=self.w, width_of=approx_width_of, roles=ROLES, from_=self.from_, to=self.to, today=self.today, today_label=self.today_label, extend_to_today=self.extend_to_today)
        return render_gantt(laid, day=self.day)


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

    def render(self) -> str:
        laid = layout_cloud_band(boxes=self.boxes, x=self.x, y=self.y, w=self.w, width_of=approx_width_of, roles=ROLES, max_node_w=self.max_node_w, assumptions=self.assumptions, conflict_label=self.conflict_label)
        return render_cloud(laid, day=self.day)


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

    def render(self) -> str:
        laid = layout_tree_band(self.root, self.x, self.y, self.w, approx_width_of, ROLES, dir_opt=self.dir_opt, max_node_w=self.max_node_w, balanced=self.balanced, layout_mode=self.layout_mode, sides=self.sides, edges_opt=self.edges_opt)
        return render_tree(laid, day=self.day)


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

    def render(self) -> str:
        laid = layout_table(columns=self.columns, rows=self.rows, x=self.x, y=self.y, w=self.w, width_of=approx_width_of, roles=ROLES, width=self.width, title=self.title, dense=self.dense, header=self.header, row_header=self.row_header, header_h=self.header_h, cell_h=self.cell_h, row_curve=self.row_curve)
        return render_table(laid, day=self.day, roles=ROLES)


@dataclass
class _Sequence:
    x: float
    y: float
    w: float
    actors: list[dict]
    steps: list[dict]
    numbered: bool = True
    day: int | str = 1

    def render(self) -> str:
        laid = layout_sequence(actors=self.actors, steps=self.steps, x=self.x, y=self.y, w=self.w, width_of=approx_width_of, roles=ROLES, numbered=self.numbered)
        return render_sequence(laid, day=self.day, roles=ROLES)


@dataclass
class _WordArt:
    x: float
    y: float
    cw: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_word_art(self.band, self.x, self.y, self.cw, approx_width_of, ROLES, "phrase")
        return render_word_art(laid, day=self.day)


class ShapesMixin:
    _elements: list[object]

    def pyramid(self, layers: list[str], *, x: float, y: float, width: float | None = None, layer_height: float = 76, apex_ratio: float = 0.3) -> None:
        """lib/dsl/figures.ts's pyramid(): layers bottom-to-top, >= 2. The per-layer geometry
        (layout_pyramid's formula in figures.py) IS byte-identical to Node — it's pure closed-
        form arithmetic — but the text WRAPPING uses this port's approximate width function."""
        if len(layers) < 2:
            raise ValueError("pyramid(layers) needs at least 2 layers, bottom to top")
        self._elements.append(_Pyramid(x=x, y=y, layers=layers, width=width if width is not None else self.width, layer_height=layer_height, apex_ratio=apex_ratio))

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
