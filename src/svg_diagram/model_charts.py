"""Diagram band methods for the "chart" family (lib/dsl/charts.ts): bars plus every chart
kind that goes through charts.py's generic layout_chart()/render_chart() dispatcher. `_Chart`
is also reused by model_stats.py (seaborn-style plots) and model_networks.py (pert/causal
loop/dependency network), since they share the exact same dispatcher. Mixed into `Diagram`
by model.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .approx_width import approx_width_of
from .bars import BarsBand, bars_band, layout_bars, render_bars
from .bubble import bubble_band
from .butterfly import butterfly_band
from .charts import layout_chart, render_chart
from .charts_base import ChartBand
from .combo import combo_band
from .harvey import harvey_band
from .heatmap import heatmap_band
from .model_shared import Renderable, _opts
from .radar import radar_band
from .sankey import sankey_band
from .stacked import mekko_band, stacked_bars_band
from .tokens import ROLES
from .tornado import tornado_band
from .treemap import treemap_band
from .waterfall import waterfall_band


@dataclass
class _Bars:
    x: float
    y: float
    w: float
    band: BarsBand
    day: int | str = 1

    def render(self) -> str:
        laid = layout_bars(self.band, self.x, self.y, self.w, approx_width_of, ROLES)
        return render_bars(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_bars(self.band, self.x, self.y, self.w, approx_width_of, ROLES)
        return laid.get("y", self.y) + laid["h"]


@dataclass
class _Chart:
    """Generic wrapper for every chart kind (heatmap, and whatever is ported next) — they all
    share one layout_chart()/render_chart() dispatcher (lib/charts.ts/lib/charts-emit.ts)."""

    x: float
    y: float
    w: float
    band: ChartBand
    day: int | str = 1

    def render(self) -> str:
        laid = layout_chart(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return render_chart(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_chart(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return laid.get("y", self.y) + laid["h"]


class ChartsMixin:
    _elements: list[Renderable]

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
        opts = _opts(
            ("unit", unit), ("decimals", decimals), ("min", min), ("max", max), ("levels", levels),
            ("rowHeader", row_header), ("corner", corner), ("scale", scale), ("cellH", cell_h),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(
            ("unit", unit), ("align", align), ("linkLabels", link_labels),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(
            ("min", min), ("max", max), ("rings", rings), ("values", values), ("unit", unit), ("fill", fill),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(
            ("unit", unit), ("percent", percent), ("strict", strict),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(
            ("unit", unit), ("axis", axis), ("connectors", connectors), ("dir", direction), ("domain", domain),
            ("plotInset", plot_inset), ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(
            ("unit", unit), ("percent", percent), ("domain", domain),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(("unit", unit), ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width))
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
        opts = _opts(
            ("base", base), ("unit", unit), ("lowLabel", low_label), ("highLabel", high_label), ("baseLabel", base_label),
            ("sort", sort), ("lowTone", low_tone), ("highTone", high_tone), ("domain", domain), ("plotInset", plot_inset),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(
            ("leftLabel", left_label), ("rightLabel", right_label),
            ("unit", unit), ("sort", sort), ("leftTone", left_tone), ("rightTone", right_tone),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(
            ("levels", levels), ("corner", corner), ("highlight", highlight),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(
            ("x", x_axis), ("y", y_axis), ("sizeTitle", size_title), ("sizeUnit", size_unit),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
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
        opts = _opts(
            ("y", y_axis), ("y2", y2_axis), ("values", values), ("stack", stack),
            ("id", id), ("height", height), ("labelRole", label_role), ("alt", alt), ("width", width),
        )
        band = combo_band(categories, series, opts)
        self._elements.append(_Chart(x=x, y=y, w=width, band=band))
