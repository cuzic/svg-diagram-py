"""The absolute-coordinate Diagram API — spec section 4/5.

This has NO Node.js counterpart: svg-diagram's real box()/connect() always go
through the full auto-layout pipeline (lib/pipeline.ts) and never accept an
explicit x/y. This module is new, Python-only code (not a port, not
golden-tested); it composes the ported drawing-layer primitives in
emit_boxes.py/emit_common.py/emit.py, which ARE golden-tested against Node.

Padding constants (BOX_PAD_X=20, BOX_PAD_Y=16) are copied from
lib/layout-util.ts for visual familiarity with Node's own box() padding —
that is a style choice, not a compatibility requirement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Literal

from .emit import emit_svg
from .emit_boxes import render_box_rect, render_connect
from .emit_common import text_lines
from .tokens import ROLES, run_color_of

BOX_PAD_X = 20
BOX_PAD_Y = 16
_LH_EM = 1.4

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


@dataclass
class Arrow:
    source: str
    target: str
    arrow: ArrowStyle = "end"
    line: LineStyle | None = None
    tone: Tone | None = None


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
        self._ids = count(1)

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
    ) -> Box:
        if width <= 0 or height <= 0:
            raise ValueError(f"box(): width and height must both be positive (got {width}, {height})")
        lines = label if isinstance(label, list) else ([label] if label else [])
        box_id = id or f"b{next(self._ids)}"
        if any(b.id == box_id for b in self.boxes):
            raise ValueError(f"box(): id {box_id!r} is already used")
        b = Box(id=box_id, x=x, y=y, width=width, height=height, lines=lines, tone=tone, fill=fill, stroke=stroke, dashed=dashed)
        self.boxes.append(b)
        return b

    def arrow(
        self,
        source: Box | str,
        target: Box | str,
        *,
        style: ArrowStyle = "end",
        line: LineStyle | None = None,
        tone: Tone | None = None,
    ) -> Arrow:
        source_id = source.id if isinstance(source, Box) else source
        target_id = target.id if isinstance(target, Box) else target
        if not any(b.id == source_id for b in self.boxes):
            raise ValueError(f"arrow(): unknown source id {source_id!r}")
        if not any(b.id == target_id for b in self.boxes):
            raise ValueError(f"arrow(): unknown target id {target_id!r}")
        a = Arrow(source=source_id, target=target_id, arrow=style, line=line, tone=tone)
        self.arrows.append(a)
        return a

    def _box_by_id(self, box_id: str) -> Box:
        for b in self.boxes:
            if b.id == box_id:
                return b
        raise KeyError(box_id)

    def _render_box(self, b: Box) -> str:
        rect = render_box_rect(x=b.x, y=b.y, w=b.width, h=b.height, tone=b.tone, dashed=b.dashed, fill=b.fill, stroke=b.stroke)
        if not b.lines:
            return rect
        # the title run has no color override of its own, so this is Node's runColorOf(tones, undefined, b.tone, day):
        # white on a solid/solid-danger box, plain text color otherwise (tokens.ts:220-222)
        fill_color = run_color_of(None, b.tone, day=1)
        text = text_lines(b.lines, x=b.x + BOX_PAD_X, top=b.y + BOX_PAD_Y, size=ROLES["title"], weight=700, fill=fill_color)
        return f"{rect}\n  {text}"

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
        """Builds the final SVG document — see Module docstring for the non-ported/ported split."""
        body = "\n\n  ".join(self._render_box(b) for b in self.boxes)
        connects = [render_connect(points=self._route(a), arrow=a.arrow, line=a.line, tone=a.tone) for a in self.arrows]
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
