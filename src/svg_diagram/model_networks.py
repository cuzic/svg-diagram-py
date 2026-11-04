"""Diagram band methods for network-of-nodes figures (lib/semnet.ts): pert/
dependency_network, plus causal_loop (lib/semnet-causal.ts). All go through the same
`_Chart` wrapper as model_charts.py's chart family. Mixed into `Diagram` by model.py.
"""

from __future__ import annotations

from .model_charts import _Chart
from .model_shared import Renderable
from .semnet import dependency_band, pert_band
from .semnet_causal import causal_band


class NetworksMixin:
    _elements: list[Renderable]

    def pert(
        self, tasks: list[dict], *, x: float, y: float, width: float, direction: str | None = None, unit: str | None = None,
        compact: bool | None = None, straighten: bool | None = None, id: str | None = None,
    ) -> None:
        """lib/semnet.ts's pert(): a PERT/CPM network — tasks (boxes) and their dependency
        arrows, laid out in layers, with the critical path highlighted. `tasks`:
        [{id, label, duration, predecessors?}]. `direction`: 'LR'(default)/'TB'."""
        band = pert_band(tasks, direction=direction, unit=unit, compact=compact, straighten=straighten, id=id)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def causal_loop(
        self, nodes: list[dict], links: list[dict], *, x: float, y: float, width: float, direction: str | None = None,
        interventions: list[dict] | None = None, layout: str | None = None, straighten: bool | None = None, id: str | None = None,
        height: float | None = None,
    ) -> None:
        """lib/dsl/charts.ts's causalLoop(): a causal loop diagram — nodes, polarity-signed
        links, the R/B loops they form, and interventions acting on them from outside.
        `nodes`: [{id, label}]. `links`: [{from, to, polarity, label?, delay?}]. `layout`:
        'layered'(default)/'ring' (a ring needs the graph to be exactly one loop of 2-8
        nodes). `interventions`: [{id, label, to, polarity, delay?}]."""
        band = causal_band(nodes, links, direction=direction, interventions=interventions, layout=layout, straighten=straighten, id=id, height=height)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))

    def dependency_network(
        self, nodes: list[dict], edges: list[dict], *, x: float, y: float, width: float, direction: str | None = None,
        node_kinds: dict | None = None, edge_types: dict | None = None, straighten: bool | None = None, id: str | None = None,
    ) -> None:
        """lib/semnet.ts's dependencyNetwork(): nodes and typed edges (depends/uses/blocks/
        relates/custom), laid out in layers, with a legend for node kinds and edge types.
        `nodes`: [{id, label, kind?}]. `edges`: [{from, to, type, weight?, label?}]."""
        band = dependency_band(nodes, edges, direction=direction, node_kinds=node_kinds, edge_types=edge_types, straighten=straighten, id=id)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))
