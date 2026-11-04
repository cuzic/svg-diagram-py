"""Diagram band methods for the seaborn-style statistics plots (lib/dsl/charts-stats.ts):
catplot/boxplot/violinplot/stripplot/swarmplot/pointplot/barplot (categorical),
displot/histplot/kdeplot/ecdfplot/rugplot (distribution), hist2d/jointplot/kde2d/pairplot
(bivariate), regplot/residplot (regression) and clustermap. All go through the same
`_Chart` wrapper as model_charts.py's chart family (charts.py's generic dispatcher). Mixed
into `Diagram` by model.py.
"""

from __future__ import annotations

from .catplot import cat_band
from .clustermap import cluster_band
from .distplot import dist_band
from .model_charts import _Chart
from .model_shared import Renderable
from .multiplot import multi_band
from .regplot import reg_band


class StatsMixin:
    _elements: list[Renderable]

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
