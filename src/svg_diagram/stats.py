"""1:1 port of lib/stats.ts — the numbers behind the seaborn-style statistical charts
(boxplot, violinplot, stripplot, swarmplot, pointplot, barplot, hist2d, jointplot, kde2d,
pairplot, regplot, residplot, clustermap). Pure functions of the values they are given;
nothing here is random.

Golden master: lib/stats.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import functools
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass


def _g(a: Sequence[float], i: int) -> float:
    return a[i] if 0 <= i < len(a) else math.nan


def _cell(m: list[list[float]], r: int, c: int) -> float:
    if 0 <= r < len(m) and 0 <= c < len(m[r]):
        return m[r][c]
    return math.nan


def total(xs: list[float]) -> float:
    return sum(xs)


def mean_of(xs: list[float]) -> float:
    return total(xs) / len(xs)


def sd_of(xs: list[float]) -> float:
    """The sample standard deviation (n - 1); 0 for a single value."""
    if len(xs) < 2:
        return 0.0
    m = mean_of(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def quantile(sorted_xs: list[float], p: float) -> float:
    """The p-quantile of sorted values by linear interpolation (numpy's default, "type 7")."""
    h = (len(sorted_xs) - 1) * p
    lo = math.floor(h)
    hi = min(len(sorted_xs) - 1, lo + 1)
    return _g(sorted_xs, lo) + (h - lo) * (_g(sorted_xs, hi) - _g(sorted_xs, lo))


@dataclass
class BoxStats:
    n: int
    min: float
    max: float
    q1: float
    median: float
    q3: float
    lo: float
    hi: float
    fliers: list[float]


def box_stats(values: list[float]) -> BoxStats:
    s = sorted(values)
    q1, median, q3 = quantile(s, 0.25), quantile(s, 0.5), quantile(s, 0.75)
    iqr = q3 - q1
    inside = [v for v in s if q1 - 1.5 * iqr <= v <= q3 + 1.5 * iqr]
    fliers = [v for v in s if v < q1 - 1.5 * iqr or v > q3 + 1.5 * iqr]
    return BoxStats(
        n=len(s), min=_g(s, 0), max=_g(s, len(s) - 1), q1=q1, median=median, q3=q3,
        lo=_g(inside, 0), hi=_g(inside, len(inside) - 1), fliers=fliers,
    )


# two-sided 95% critical values of Student's t for 1..30 degrees of freedom
_T95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.16, 2.145, 2.131,
        2.12, 2.11, 2.101, 2.093, 2.086, 2.08, 2.074, 2.069, 2.064, 2.06, 2.056, 2.052, 2.048, 2.045, 2.042]


def t_critical_95(df: float) -> float:
    if df < 1:
        return math.nan
    if df <= 30:
        return _g(_T95, int(df) - 1)
    z = 1.959964  # Cornish-Fisher expansion about the normal quantile (error < 0.001 beyond 30 degrees of freedom)
    return z + (z ** 3 + z) / (4 * df) + (5 * z ** 5 + 16 * z ** 3 + 3 * z) / (96 * df * df)


def error_bar(values: list[float], kind: str) -> tuple[float, float] | None:
    """The error bar of a mean: the 95% confidence interval (t distribution), ±1 standard
    deviation, ±1 standard error, or the full range. None when n = 1 (nothing to say about
    spread)."""
    n, m = len(values), mean_of(values)
    if kind == "none":
        return None
    if kind == "range":
        return None if n < 2 else (min(values), max(values))
    if n < 2:
        return None
    sd = sd_of(values)
    half = sd if kind == "sd" else sd / math.sqrt(n) if kind == "se" else t_critical_95(n - 1) * sd / math.sqrt(n)
    return (m - half, m + half)


def kde(values: list[float], grid: list[float], bw_scale: float = 1) -> dict:
    """Gaussian kernel density estimate at each of `grid`, with Scott's bandwidth (the standard
    deviation times n^(-1/5): what seaborn uses). Integrates to 1."""
    n = len(values)
    bw = max(sd_of(values) * n ** -0.2 * bw_scale, 1e-12)
    k = 1 / (n * bw * math.sqrt(2 * math.pi))
    density = [k * sum(math.exp(-0.5 * ((g - v) / bw) ** 2) for v in values) for g in grid]
    return {"density": density, "bw": bw}


def swarm_offsets(at: list[float], d: float, max_off: float) -> list[float] | None:
    """A beeswarm: each value gets a sideways offset (px) so that no two points of diameter `d`
    touch, as near the centre line as it can be. `at` are the positions along the value axis
    (px). Returns the offsets in the order of `at`, or None if a point would need to go further
    than `maxOff` from the centre."""
    order = sorted(range(len(at)), key=lambda i: _g(at, i))
    placed: list[tuple[float, float]] = []
    out = [0.0] * len(at)
    for i in order:
        u = _g(at, i)
        near = [(pu, po) for pu, po in placed if abs(pu - u) < d]
        cands = [0.0]
        for pu, po in near:
            dx = math.sqrt(d * d - (pu - u) ** 2)
            cands.append(po + dx)
            cands.append(po - dx)
        def _nearest_cmp(a: float, b: float) -> int:
            d = (abs(a) - abs(b)) or (b - a)
            return (d > 0) - (d < 0)

        cands.sort(key=functools.cmp_to_key(_nearest_cmp))
        off = next((x for x in cands if all(math.hypot(pu - u, po - x) >= d - 1e-6 for pu, po in near)), None)
        if off is None or abs(off) > max_off:
            return None
        placed.append((u, off))
        out[i] = off
    return out


def bin_counts(values: list[float], edges: list[float]) -> list[float]:
    """Counts of `values` in the classes between `edges` (a value on an edge belongs to the
    class above it, the largest value to the last class)."""
    n = len(edges) - 1
    out = [0.0] * n
    w = (_g(edges, n) - _g(edges, 0)) / n
    for v in values:
        k = min(n - 1, max(0, math.floor((v - _g(edges, 0)) / w + 1e-9)))
        out[k] = out[k] + 1
    return out


def bin_index(v: float, edges: list[float]) -> int:
    """The index of the class of `edges` that `v` falls in (the same rule as bin_counts)."""
    n = len(edges) - 1
    return min(n - 1, max(0, math.floor((v - _g(edges, 0)) / ((_g(edges, n) - _g(edges, 0)) / n) + 1e-9)))


@dataclass
class PolyFit:
    order: int
    coef: list[float]
    r2: float
    n: int
    at: Callable[[float], float]
    rss: float
    half: Callable[[float], float] | None = None


def poly_fit(xs: list[float], ys: list[float], order: int) -> PolyFit:
    """A least-squares polynomial of `order` 1..3 (the x values are centred and scaled first,
    so a high order stays well conditioned) with the analytic 95% confidence band of the fitted
    mean: t(n - p) * s * sqrt(v' (X'X)^-1 v)."""
    n = len(xs)
    p = order + 1
    mx, sx = mean_of(xs), sd_of(xs) or 1

    def row(x: float) -> list[float]:
        z = (x - mx) / sx
        return [z ** k for k in range(p)]

    big_x = [row(x) for x in xs]
    a = [[sum(_g(r, i) * _g(r, j) for r in big_x) for j in range(p)] for i in range(p)]
    b = [sum(_g(r, i) * _g(ys, k) for k, r in enumerate(big_x)) for i in range(p)]
    # Gauss-Jordan on [A | I | b]: the solution and the inverse together
    m = [list(a[i]) + [1.0 if i == j else 0.0 for j in range(p)] + [b[i]] for i in range(p)]
    for c in range(p):
        piv = c
        for r in range(c + 1, p):
            if abs(_cell(m, r, c)) > abs(_cell(m, piv, c)):
                piv = r
        m[c], m[piv] = m[piv], m[c]
        d = _cell(m, c, c)
        if abs(d) < 1e-12:
            raise ValueError("polyFit: the x values do not determine a polynomial of this order")
        mc = [v / d for v in m[c]]
        m[c] = mc
        for r in range(p):
            if r != c:
                f = _cell(m, r, c)
                m[r] = [v - f * _g(mc, k) for k, v in enumerate(m[r])]
    beta = [_g(r, 2 * p) for r in m]
    inv = [r[p:2 * p] for r in m]

    def at(x: float) -> float:
        return sum(v * _g(beta, k) for k, v in enumerate(row(x)))

    my = mean_of(ys)
    rss = sum((_g(ys, i) - at(x)) ** 2 for i, x in enumerate(xs))
    tss = sum((y - my) ** 2 for y in ys)
    df = n - p
    s = math.sqrt(rss / df) if df > 0 else math.nan
    t = t_critical_95(df)

    half: Callable[[float], float] | None = None
    if df > 0:
        def _half(x: float) -> float:
            v = row(x)
            inner = sum(vi * sum(q * _g(v, j) for j, q in enumerate(inv[i])) for i, vi in enumerate(v))
            return t * s * math.sqrt(max(0.0, inner))

        half = _half

    return PolyFit(order=order, coef=beta, r2=(1 - rss / tss if tss > 0 else 1), n=n, at=at, rss=rss, half=half)


def kde2d(xs: list[float], ys: list[float], gx: list[float], gy: list[float]) -> dict:
    """A 2-D Gaussian kernel density estimate on the grid gx x gy (z[j][i] is at gx[i], gy[j]);
    each axis has Scott's bandwidth for two dimensions (the standard deviation times
    n^(-1/6))."""
    n = len(xs)
    bwx = max(sd_of(xs) * n ** (-1 / 6), 1e-12)
    bwy = max(sd_of(ys) * n ** (-1 / 6), 1e-12)
    k = 1 / (n * 2 * math.pi * bwx * bwy)
    ex = [[math.exp(-0.5 * ((g - x) / bwx) ** 2) for x in xs] for g in gx]
    ey = [[math.exp(-0.5 * ((g - y) / bwy) ** 2) for y in ys] for g in gy]
    z = [[k * sum(_cell(ex, i, mi) * _cell(ey, j, mi) for mi in range(n)) for i in range(len(gx))] for j in range(len(gy))]
    return {"z": z, "bwx": bwx, "bwy": bwy}


@dataclass
class Merge:
    a: int
    b: int
    height: float
    size: int


def average_linkage(data: list[list[float]]) -> list[Merge]:
    """Agglomerative clustering with average linkage (UPGMA) on the Euclidean distances between
    the rows of `data`. Leaves are 0..n-1, the k-th merge makes node n + k. Ties go to the pair
    with the smaller indices, so the same data always gives the same tree."""
    n = len(data)

    def dist(a: list[float], b: list[float]) -> float:
        return math.sqrt(sum((v - _g(b, i)) ** 2 for i, v in enumerate(a)))

    live: dict[int, int] = {i: 1 for i in range(n)}  # id -> size

    def key(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)

    d: dict[tuple[int, int], float] = {}
    for i in range(n):
        for j in range(i + 1, n):
            d[key(i, j)] = dist(data[i], data[j])
    out: list[Merge] = []
    for step in range(n - 1):
        best: tuple[int, int] | None = None
        bd = math.inf
        ids = sorted(live.keys())
        for xi in range(len(ids)):
            for yi in range(xi + 1, len(ids)):
                ix, iy = ids[xi], ids[yi]
                v = d[key(ix, iy)]
                if v < bd - 1e-12:
                    bd = v
                    best = (ix, iy)
        assert best is not None  # >= 2 live ids remain at every step < n - 1, and the first pair compared always beats bd=inf
        a, b = best
        sa, sb = live[a], live[b]
        node_id = n + step
        for o in ids:
            if o != a and o != b:
                d[key(node_id, o)] = (sa * d[key(a, o)] + sb * d[key(b, o)]) / (sa + sb)
        del live[a]
        del live[b]
        live[node_id] = sa + sb
        out.append(Merge(a=a, b=b, height=bd, size=sa + sb))
    return out


def dendrogram_order(merges: list[Merge], n: int) -> dict:
    """The leaves of a tree from average_linkage in dendrogram order (the child holding the
    smaller leaf first), and where each node sits (the mean of its children's positions)."""

    def node(node_id: int) -> Merge:
        return merges[node_id - n]

    def min_leaf(node_id: int) -> int:
        return node_id if node_id < n else min(min_leaf(node(node_id).a), min_leaf(node(node_id).b))

    def kids(node_id: int) -> tuple[int, int]:
        m = node(node_id)
        return (m.a, m.b) if min_leaf(m.a) <= min_leaf(m.b) else (m.b, m.a)

    def seq(node_id: int) -> list[int]:
        if node_id < n:
            return [node_id]
        a, b = kids(node_id)
        return seq(a) + seq(b)

    order = [0] if n == 1 else seq(n + len(merges) - 1)
    at = {leaf: i for i, leaf in enumerate(order)}
    pos = [0.0] * (n + len(merges))
    for i in range(n):
        pos[i] = at[i]
    for k, m in enumerate(merges):
        pos[n + k] = (_g(pos, m.a) + _g(pos, m.b)) / 2
    return {"order": order, "pos": pos}


def lowess_fit(xs: list[float], ys: list[float], frac: float = 2 / 3, iterations: int = 3):
    """LOWESS (locally weighted linear regression, Cleveland 1979) as a function of x: at x0 the
    nearest `frac` of the points are fitted by a weighted line (tricube weights), and
    `iterations` rounds of bisquare weights on the residuals make it robust to outliers
    (statsmodels' defaults: frac 2/3, 3 iterations). Evaluated at any x, so a smooth curve can be
    drawn without interpolating between data points."""
    n = len(xs)
    k = max(2, min(n, math.ceil(frac * n)))
    rw = [1.0] * n

    def at(x0: float, w: list[float]) -> float:
        d = [abs(x - x0) for x in xs]
        h = max(_g(sorted(d), k - 1), 1e-12)
        sw = swx = swy = swxx = swxy = 0.0
        for i, di in enumerate(d):
            u = di / h
            if u >= 1:
                continue
            wi = _g(w, i) * (1 - u ** 3) ** 3
            sw += wi
            swx += wi * _g(xs, i)
            swy += wi * _g(ys, i)
            swxx += wi * _g(xs, i) ** 2
            swxy += wi * _g(xs, i) * _g(ys, i)
        if sw <= 0:
            return mean_of(ys)
        den = sw * swxx - swx * swx
        if abs(den) < 1e-12 * max(1.0, sw * swxx):
            return swy / sw
        slope = (sw * swxy - swx * swy) / den
        return (swy - slope * swx) / sw + slope * x0

    final = rw
    for _ in range(iterations):
        res = [_g(ys, i) - at(x, rw) for i, x in enumerate(xs)]
        s = sorted(abs(r) for r in res)
        mid = len(s) >> 1
        med = s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
        if med < 1e-12:
            break
        rw = [(1 - (abs(r) / (6 * med)) ** 2) ** 2 if abs(r) / (6 * med) < 1 else 0.0 for r in res]
        final = rw

    return lambda x0: at(x0, final)
