"""Diagram band methods for the "flow shapes" domain (lib/flow-shapes.ts): chevron/funnel/
cycle/venn/concentric/emblem/value_chain — all share one layout_flow_shape()/
render_flow_shape() pair. Mixed into `Diagram` by model.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .approx_width import approx_width_of
from .flow_shapes import (
    chevron_band,
    concentric_band,
    cycle_band,
    emblem_band,
    funnel_band,
    layout_flow_shape,
    render_flow_shape,
    value_chain_band,
    venn_band,
)
from .model_shared import Renderable
from .tokens import ROLES


@dataclass
class _FlowShape:
    x: float
    y: float
    cw: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_flow_shape(self.band, self.x, self.y, self.cw, approx_width_of, ROLES, "phrase")
        return render_flow_shape(laid, day=self.day)


class FlowShapesMixin:
    _elements: list[Renderable]

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

    def emblem(self, items: list[dict], *, x: float, y: float, width: float, shape: str | None = None, gap: float | None = None, min_size: float | None = None) -> None:
        """lib/flow-shapes.ts's emblem(): a word or two inside a circle/square/triangle/.../cylinder.
        `items`: [{label, sub?, shape?, id?, tone?}]."""
        band = emblem_band(items, shape=shape, gap=gap, min_size=min_size)
        self._elements.append(_FlowShape(x=x, y=y, cw=width, band=band))

    def value_chain(self, *, primary: list[dict], x: float, y: float, width: float, support: list[dict] | None = None, margin: str | bool | None = None, titles: tuple | bool | None = None) -> None:
        """lib/flow-shapes.ts's valueChain(): Porter's value chain."""
        band = value_chain_band(support=support, primary=primary, margin=margin, titles=titles)
        self._elements.append(_FlowShape(x=x, y=y, cw=width, band=band))
