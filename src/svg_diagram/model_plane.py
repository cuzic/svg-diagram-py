"""Diagram band methods for the coordinate-plane family (lib/dsl/figures.ts's plane(),
lib/dsl/charts.ts's lines()/burndown()/burnup()/strategyCanvas() which all work out into a
plane()) and quadrant() (lib/dsl/figures.ts, its own standalone band type). Mixed into
`Diagram` by model.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .approx_width import approx_width_of
from .lines import burndown_band, burnup_band, lines_band, strategy_canvas_band
from .model_shared import Renderable
from .plane import layout_plane, plane_band, render_plane
from .quadrant import layout_quadrant, quadrant_band, render_quadrant
from .tokens import ROLES


@dataclass
class _Plane:
    """plane() is a standalone band type ("plane"), not part of the "chart" family — its own
    layout_plane()/render_plane() pair (lib/plane.ts/lib/emit-figures.ts's renderPlane())."""

    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_plane(self.band, self.x, self.y, self.w, approx_width_of, ROLES)
        return render_plane(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_plane(self.band, self.x, self.y, self.w, approx_width_of, ROLES)
        return laid.get("y", self.y) + laid["h"]


@dataclass
class _Quadrant:
    """quadrant() is a standalone band type ("quadrant"), not part of the "chart" family —
    its own layout_quadrant()/render_quadrant() pair (lib/quadrant.ts/lib/emit-figures.ts's
    renderQuadrant())."""

    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_quadrant(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return render_quadrant(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_quadrant(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return laid.get("y", self.y) + laid["h"]


class PlaneMixin:
    _elements: list[Renderable]

    def quadrant(self, opts: dict, *, x: float, y: float, width: float) -> None:
        """lib/dsl/figures.ts's quadrant(): a classification matrix (2x2, 3x3 or any N x M
        cells) — items placed in a cell or at a coordinate, optional bubble sizes (area
        proportional to value), movement arrows, free-shaped regions, and the named presets
        of management frameworks ('bcg' | 'ge' | 'ansoff' | 'nineBox' | 'impactEffort' |
        'risk' | 'stakeholder' | 'positioning' | 'eisenhower'). Unlike most other band
        methods, `opts` is passed through as Node's own nested shape (not exploded into
        keyword arguments, same reasoning as plane()): {preset?, x?: {title, low?, high?,
        reversed?}, y?: {...}, grid?: [cols, rows], cells?: [[{title?, note?, tone?}, ...]],
        items?: [{id?, label, cell?: [col, row] | at?: [x, y], size?, tone?, group?}],
        arrows?: [{from, to, label?, dashed?}], sizeTitle?, sizeUnit?, groups?, crosshair?,
        regions?: [{title, note?, tone?, points, at?}], height?, width?, allowEmpty?, id?,
        reveal?, until?}. The layout formula (including the item-placement collision search
        and the row-growth retry loop) IS byte-identical to Node (golden-tested live); only
        text widths use this port's approximation."""
        band = quadrant_band(opts)
        self._elements.append(_Quadrant(x=x, y=y, w=width, band=band))

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
