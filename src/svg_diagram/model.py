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

This file holds `Diagram` itself plus the band-agnostic "basics" (box/raw/caption/group/
banner/legend/status/arrow/row/grid, and rendering/saving). Everything domain-specific
(charts, seaborn-style stats plots, process diagrams, flow shapes, plane-family figures,
shapes like tree/table/timeline/gantt/...) lives in its own `model_*.py` module as a mixin,
each a cohesive "core" for its own domain, composed together here. An element's `.render()`
is defined on the element's own dataclass (in whichever module owns that domain) rather
than in a central dispatch function, so adding a new band type never requires touching this
file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Callable, Literal

from .approx_width import approx_width_of
from .emit import emit_svg
from .emit_boxes import render_banner, render_box_rect, render_caption, render_connect, render_group_rect, render_raw, render_status, render_step_badge, render_stamp, render_tag
from .emit_common import LH_EM, text_lines
from .layout_util import BOX_PAD_X, BOX_PAD_Y, LEGEND_ROW_H, STAMP_PAD_X, STEP_INDENT, TAG_H, TAG_PAD_X, grid_child_geometry, row_child_geometry
from .legend import render_legend_item
from .model_charts import ChartsMixin
from .model_flow_shapes import FlowShapesMixin
from .model_networks import NetworksMixin
from .model_plane import PlaneMixin
from .model_process import ProcessMixin
from .model_shapes import ShapesMixin
from .model_shared import ArrowStyle, LineStyle, Renderable, Tone
from .model_stats import StatsMixin
from .tokens import ROLES, run_color_of, text_color_of


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

    def render(self) -> str:
        # Mirrors Node's renderBox() concatenation exactly — it is NOT a uniform join: frame
        # carries its own trailing "\n  ", badge/tag need a caller-added LEADING "\n  ", and
        # stamp already carries its own leading "\n  " (lib/emit-boxes.ts:89-95).
        out = ""
        if self.frame:
            out += render_box_rect(x=self.x, y=self.y, w=self.width, h=self.height, tone=self.tone, dashed=self.dashed, dim=self.dim, fill=self.fill, stroke=self.stroke) + "\n  "
        if self.lines:
            # the title run has no color override of its own, so this is Node's runColorOf(tones, undefined, b.tone, day):
            # white on a solid/solid-danger box, plain text color otherwise (tokens.ts:220-222)
            fill_color = run_color_of(None, self.tone, day=1)
            # Node only indents the FIRST (title) line for a step badge; this port has no
            # title/body distinction, so — as a documented simplification — every line shifts.
            indent = STEP_INDENT if self.step is not None else 0
            out += text_lines(self.lines, x=self.x + BOX_PAD_X + indent, top=self.y + BOX_PAD_Y, size=ROLES["title"], weight=700, fill=fill_color)
        if self.step is not None:
            title_baseline_y = self.y + BOX_PAD_Y + ROLES["title"]
            out += "\n  " + render_step_badge(x=self.x, pad_x=BOX_PAD_X, title_baseline_y=title_baseline_y, step=self.step, tone=self.tone, dim=self.dim)
        if self.tag is not None:
            tag_w = approx_width_of(self.tag, 14, 700) + 2 * TAG_PAD_X
            tx = self.x + 8 + (self.width - 16 - tag_w) * self.tag_at
            tag_box = {"x": tx, "y": self.y - TAG_H / 2, "w": tag_w, "h": TAG_H}
            out += "\n  " + render_tag(tag_box=tag_box, tag=self.tag, tag_tone=self.tag_tone, tone=self.tone, dim=self.dim)
        if self.stamp is not None:
            stamp_w = approx_width_of(self.stamp, ROLES["note"], 400) + 2 * STAMP_PAD_X
            out += render_stamp(x=self.x, y=self.y, w=self.width, h=self.height, stamp=self.stamp, stamp_w=stamp_w, note_size=ROLES["note"])
        return out

    def bottom(self) -> float:
        return self.y + self.height


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

    def render(self) -> str:
        return render_caption(x=self.x, y=self.y, w=self.w, text=self.text, size=ROLES["title"], align=self.align, tone=self.tone)

    def bottom(self) -> float:
        return self.y + ROLES["title"] * LH_EM


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

    def render(self) -> str:
        # lib/emit-boxes.ts:98-101 renderGroup(): rect and stamp concatenate directly
        # (renderStamp already carries its own leading "\n  "); the title caption is a
        # SEPARATE top-level band in Node (lib/layout-util.ts's groupTitleBand()), so it
        # joins here the same way two bands join in the body list ("\n\n  ").
        out = render_group_rect(x=self.x, y=self.y, w=self.w, h=self.h, tone=self.tone, dashed=self.dashed, dim=self.dim)
        if self.stamp:
            stamp_w = approx_width_of(self.stamp, ROLES["note"], 400) + 2 * STAMP_PAD_X
            out += render_stamp(x=self.x, y=self.y, w=self.w, h=self.h, stamp=self.stamp, stamp_w=stamp_w, note_size=ROLES["note"])
        if self.title:
            title_color = text_color_of("accent" if self.tone == "accent" else None, 1)
            title_svg = text_lines([self.title], x=self.x + BOX_PAD_X, top=self.y + BOX_PAD_Y, size=ROLES["title"], weight=700, fill=title_color)
            out += "\n\n  " + title_svg
        return out

    def bottom(self) -> float:
        return self.y + self.h


@dataclass
class _Banner:
    x: float
    y: float
    w: float
    h: float
    lines: list[str] = field(default_factory=list)
    tone: Tone | None = None

    def render(self) -> str:
        return render_banner(x=self.x, y=self.y, w=self.w, h=self.h, lines=self.lines, size=ROLES["title"], tone=self.tone)

    def bottom(self) -> float:
        return self.y + self.h


@dataclass
class _Legend:
    items: list[dict]

    def render(self) -> str:
        return "\n  ".join(render_legend_item(note_size=ROLES["note"], **item) for item in self.items)

    def bottom(self) -> float:
        return max((item["y"] + LEGEND_ROW_H for item in self.items), default=0.0)


@dataclass
class _Raw:
    x: float
    y: float
    w: float
    h: float
    draw: Callable[[dict], str]

    def render(self) -> str:
        return render_raw(x=self.x, y=self.y, w=self.w, h=self.h, day=1, draw=self.draw)

    def bottom(self) -> float:
        return self.y + self.h


@dataclass
class _Status:
    x: float
    y: float
    width: float
    text: str
    status: str
    height: float = 24
    size: float = 14

    def render(self) -> str:
        text_y = self.y + self.height / 2 + self.size * 0.38
        return render_status(x=self.x, y=self.y, w=self.width, h=self.height, text_y=text_y, text=self.text, status=self.status, size=self.size)

    def bottom(self) -> float:
        return self.y + self.height


def _edge_point(box: Box, side: str) -> dict:
    cx, cy = box.x + box.width / 2, box.y + box.height / 2
    return {
        "left": {"x": box.x, "y": cy},
        "right": {"x": box.x + box.width, "y": cy},
        "top": {"x": cx, "y": box.y},
        "bottom": {"x": cx, "y": box.y + box.height},
        "center": {"x": cx, "y": cy},
    }[side]


AUTO_HEIGHT_MARGIN = 24  # this port's own convention (not a port of anything in lib/): room below the lowest element's content


class Diagram(ShapesMixin, FlowShapesMixin, ProcessMixin, ChartsMixin, StatsMixin, NetworksMixin, PlaneMixin):
    """spec section 4: ``Diagram(width, height)``, ``.box(...)``, ``.arrow(start, end)``, ``.save(path)``.

    ``height="auto"`` (this port's own addition, not a Node option — box()/row()/grid()'s
    absolute-coordinate API has no auto-layout to size a canvas from in the first place)
    sizes the canvas to the lowest element's content instead of a number fixed up front,
    via each element's own ``bottom()`` (see model_shared.py's Renderable docstring)."""

    def __init__(self, width: float, height: float | Literal["auto"]):
        if isinstance(height, str) and height != "auto":
            raise ValueError(f"Diagram(width, height): height must be a positive number or 'auto' (got {height!r})")
        if width <= 0 or (height != "auto" and height <= 0):
            raise ValueError(f"Diagram(width, height) must both be positive (got {width}, {height})")
        self.width = width
        self.height = height
        self.boxes: list[Box] = []
        self.arrows: list[Arrow] = []
        self._elements: list[Renderable] = []
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

    def status(self, text: str, *, x: float, y: float, width: float, status: str = "draft", height: float = 24, size: float = 14) -> None:
        """diagram({status}): a dashed-outline pill — position is a new simplified formula, see render_status()."""
        self._elements.append(_Status(x=x, y=y, width=width, text=text, status=status, height=height, size=size))

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
        body = "\n\n  ".join(el.render() for el in self._elements)
        connects = [render_connect(points=self._route(a), arrow=a.arrow, line=a.line, tone=a.tone, label=a.label, chip=a.chip, label_at=a.label_at) for a in self.arrows]
        connect_svg = "\n\n  ".join(connects)
        # Checking self.arrows alone misses any element (sequence() messages, swimlane()
        # steps, legend() line items, ...) that draws its own marker-end/marker-start via
        # arrow_markers() — mirrors TS's usesArrows() (lib/emit.ts) without needing to
        # enumerate every element kind that can embed an arrow.
        has_arrow = 'url(#dsl-arrow)"' in body or 'url(#dsl-arrow)"' in connect_svg
        given_height = self.height
        height = self._auto_height() if isinstance(given_height, str) else given_height
        return emit_svg(width=self.width, height=height, body=body, connect_svg=connect_svg, has_arrow=has_arrow)

    def _auto_height(self) -> float:
        """`Diagram(width, height="auto")`: the canvas just tall enough for every element's
        own content (each element's `bottom()`, plus `AUTO_HEIGHT_MARGIN` below the
        lowest one) — this port's own convention, not a Node option."""
        return max((el.bottom() for el in self._elements), default=0.0) + AUTO_HEIGHT_MARGIN

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
