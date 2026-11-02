"""1:1 port of lib/charts-dist.ts's layoutDist() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and lib/charts-dsl.ts's distBand() — the seaborn-style
distribution plots (histplot/kdeplot/ecdfplot/rugplot/displot), built on lib/stats.ts's
kde()/binCounts() and lib/qc.ts's histogramBins() (its one function this port needs is
reimplemented here rather than porting the whole file, same reasoning as other *Texts()
omissions — qc.ts's other exports are process-capability statistics this port does not use).

distTexts()/distAxes() (Node's text-measurement-batching / facet-axis-sharing helpers) are
not ported — same reasoning as the other chart kinds' *Texts() helpers; facet() sharing is
out of scope until facet() itself is ported.

Golden master: lib/charts-dist.ts + lib/qc.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import json
import math

from .charts_base import CHART_DASH as DASH
from .charts_base import CHART_TONES as TONES
from .charts_base import Canvas, _to_precision, check_ids, check_range, check_text, common_chart_opts, fail, finite_num, nice_near, nice_scale, num_text
from .emit_common import js_num, round1
from .stats import bin_counts, kde

KINDS: list[str] = ["hist", "kde", "ecdf", "rug"]
DIST_FN: dict[str, str] = {"hist": "histplot", "kde": "kdeplot", "ecdf": "ecdfplot", "rug": "rugplot"}
NAME: dict[str, str] = {"hist": "ヒストグラム", "kde": "密度曲線（KDE）", "ecdf": "経験累積分布（ECDF）", "rug": "ラグプロット"}
STATS: list[str] = ["count", "density", "probability", "percent"]

_MAX_CLASSES = 60


def _exact(n: float) -> str:
    """lib/qc.ts:9 exact()."""
    return js_num(_to_precision(n, 12))


def _histogram_bins(values: list[float], bins: int | None = None, width: float | None = None) -> dict:
    """lib/qc.ts:73-87 histogramBins() (only the {bins?, width?} overload; `include` is not
    used by charts-dist.ts and is not ported)."""
    dlo, dhi = min(values), max(values)
    want = bins if bins is not None else math.ceil(math.log2(len(values))) + 1
    w = width if width is not None else nice_near((dhi - dlo or abs(dhi) or 1) / want)
    lo, hi = dlo, dhi
    start = math.floor(lo / w + 1e-9) * w
    n = max(1, math.ceil((hi - start) / w - 1e-9))
    if n > _MAX_CLASSES:
        raise ValueError(f"histogram(): {n} classes of width {_exact(w)} (at most {_MAX_CLASSES}): use a wider width, fewer bins, or limits closer to the data")
    if start + n * w <= hi - 1e-9:
        n += 1
    edges = [_to_precision(start + i * w, 12) for i in range(n + 1)]
    counts = [0.0] * n
    for v in values:
        k = min(n - 1, max(0, math.floor((v - start) / w + 1e-9)))
        counts[k] += 1
    return {"edges": edges, "counts": counts, "width": w}


def resolve_dist(who: str, data, opts: dict | None, default_kind: str) -> dict:
    """lib/charts-dist.ts:44-76 resolveDist()."""
    opts = opts or {}
    if isinstance(data, dict):
        raw = [{"label": label, "values": list(values)} for label, values in data.items()]
    elif isinstance(data, list) and data and all(isinstance(v, (int, float)) for v in data):
        raw = [{"label": "", "values": list(data)}]
    else:
        raw = [dict(g) for g in data]
    if len(raw) == 0:
        fail(who, "needs at least one group of values")
    if len(raw) > len(TONES):
        fail(who, f"at most {len(TONES)} groups (got {len(raw)})")
    check_ids(who, [g.get("id") for g in raw], opts.get("id"))
    kind_opt = opts.get("kind")
    kinds = [default_kind] if kind_opt is None else (list(kind_opt) if isinstance(kind_opt, list) else [kind_opt])
    if len(kinds) == 0 or any(k not in KINDS for k in kinds):
        fail(who, f"kind must be {' / '.join(KINDS)} (or a list of them; got {json.dumps(kind_opt)})")
    if len(set(kinds)) != len(kinds):
        fail(who, "each kind may appear once in kind")
    if "ecdf" in kinds and ("hist" in kinds or "kde" in kinds):
        fail(who, "ecdf is a cumulative share on its own axis: it does not go with hist / kde (use rug with it)")
    groups = []
    for i, g in enumerate(raw):
        if len(raw) > 1:
            check_text(who, f"group {i + 1}'s label", g["label"])
        if not isinstance(g.get("values"), list) or len(g["values"]) == 0:
            fail(who, f"{(chr(34) + g['label'] + chr(34)) if g['label'] else 'the data'} has no values")
        values = [finite_num(who, f"{(chr(34) + g['label'] + chr(34) + ' ') if g['label'] else ''}value {k + 1}", v) for k, v in enumerate(g["values"])]
        if "kde" in kinds and (len(values) < 2 or min(values) == max(values)):
            fail(who, f"{(chr(34) + g['label'] + chr(34)) if g['label'] else 'the data'}: a density curve needs at least two different values")
        out: dict = {"label": g["label"], "values": values}
        if g.get("id") is not None:
            out["id"] = g["id"]
        groups.append(out)
    stat = opts.get("stat")
    if stat is None:
        stat = "probability" if "ecdf" in kinds else "density" if "kde" in kinds else "count"
    if stat not in STATS:
        fail(who, f"stat must be {' / '.join(STATS)} (got {opts.get('stat')!r})")
    if "kde" in kinds and "hist" not in kinds and stat != "density":
        fail(who, f"a density curve alone is a density (stat: '{stat}' needs bars to be a count of; add 'hist' to kind)")
    element = opts.get("element") or "bars"
    bw = opts.get("bw") if opts.get("bw") is not None else 1
    if element not in ("bars", "step"):
        fail(who, f"element must be bars or step (got {opts.get('element')!r})")
    if not (bw > 0) or not math.isfinite(bw):
        fail(who, f"bw must be a number > 0 (got {opts.get('bw')})")
    if opts.get("bins") is not None and opts.get("binWidth") is not None:
        fail(who, "give bins or binWidth, not both")
    if opts.get("bins") is not None and not (isinstance(opts["bins"], int) and not isinstance(opts["bins"], bool) and opts["bins"] >= 1):
        fail(who, f"bins must be a whole number >= 1 (got {opts.get('bins')})")
    if opts.get("binWidth") is not None and not (opts["binWidth"] > 0 and math.isfinite(opts["binWidth"])):
        fail(who, f"binWidth must be a number > 0 (got {opts.get('binWidth')})")
    edges = None
    if "hist" in kinds:
        all_vals = [v for gr in groups for v in gr["values"]]
        try:
            edges = _histogram_bins(all_vals, opts.get("bins"), opts.get("binWidth"))["edges"]
        except ValueError as e:
            fail(who, str(e).removeprefix("histogram(): "))

    spec: dict = {"groups": groups, "kinds": kinds, "label": opts.get("label") or "", "unit": opts.get("unit") or "", "stat": stat, "element": element, "bw": bw}
    x_range, y_range = check_range(who, opts, "xRange"), check_range(who, opts, "yRange")
    if x_range:
        spec["xRange"] = x_range
    if y_range:
        spec["yRange"] = y_range
    if opts.get("bins") is not None:
        spec["bins"] = opts["bins"]
    if opts.get("binWidth") is not None:
        spec["binWidth"] = opts["binWidth"]
    if edges is not None:
        spec["edges"] = edges
    return spec


def _ecdf_stat(s: dict) -> str:
    return "count" if s["stat"] == "count" else "percent" if s["stat"] == "percent" else "proportion"


def _y_name(s: dict) -> str:
    if "ecdf" in s["kinds"]:
        es = _ecdf_stat(s)
        return "累積件数" if es == "count" else "累積割合（%）" if es == "percent" else "累積割合"
    return {"count": "件数", "density": "密度", "probability": "割合", "percent": "割合（%）"}[s["stat"]]


def _height_of(stat: str, c: float, n: int, w: float) -> float:
    return c if stat == "count" else c / (n * w) if stat == "density" else c / n if stat == "probability" else 100 * c / n


def _factor(stat: str, n: int, w: float) -> float:
    return n * w if stat == "count" else 1 if stat == "density" else w if stat == "probability" else 100 * w


def _class_w(s: dict) -> float:
    e = s.get("edges")
    return (e[-1] - e[0]) / (len(e) - 1) if e else 1


def dist_alt(s: dict) -> str:
    """lib/charts-dist.ts:87-90 distAlt()."""

    def mean(v: list[float]) -> float:
        return sum(v) / len(v)

    kinds_txt = "＋".join(NAME[k] for k in s["kinds"])
    label_txt = f"（{s['label']}）" if s["label"] else ""
    groups_txt = "、".join(
        f"{(g['label'] + ' ') if g['label'] else ''}n={len(g['values'])} 平均 {num_text(mean(g['values']))}{s['unit']} 範囲 {num_text(min(g['values']))}〜{num_text(max(g['values']))}{s['unit']}"
        for g in s["groups"]
    )
    return f"{kinds_txt}{label_txt}: {groups_txt}"


def _plan(s: dict) -> dict:
    """lib/charts-dist.ts:92-111 plan()."""
    all_vals = [v for g in s["groups"] for v in g["values"]]
    lo, hi = min(all_vals), max(all_vals)
    bws = [kde(g["values"], [0], s["bw"])["bw"] for g in s["groups"]] if "kde" in s["kinds"] else []
    if s.get("edges"):
        lo, hi = min(lo, s["edges"][0]), max(hi, s["edges"][-1])
    if bws:
        lo = min([lo] + [min(g["values"]) - 2 * bws[i] for i, g in enumerate(s["groups"])])
        hi = max([hi] + [max(g["values"]) + 2 * bws[i] for i, g in enumerate(s["groups"])])
    if s.get("xRange"):
        lo, hi = min(lo, s["xRange"][0]), max(hi, s["xRange"][1])
    xs = nice_scale(lo, hi)
    edges = s.get("edges")
    bars = []
    if edges:
        for g in s["groups"]:
            counts = bin_counts(g["values"], edges)
            bars.append([{"x0": edges[i], "x1": edges[i + 1], "y": _height_of(s["stat"], c, len(g["values"]), _class_w(s))} for i, c in enumerate(counts)])
    curves = []
    if "kde" in s["kinds"]:
        for g in s["groups"]:
            grid = [xs["min"] + (xs["max"] - xs["min"]) * i / 120 for i in range(121)]
            f = _factor(s["stat"], len(g["values"]), _class_w(s))
            density = kde(g["values"], grid, s["bw"])["density"]
            curves.append([{"x": grid[i], "y": d * f} for i, d in enumerate(density)])
    if "ecdf" in s["kinds"]:
        top = max(len(g["values"]) for g in s["groups"]) if s["stat"] == "count" else 100 if s["stat"] == "percent" else 1
    else:
        flat_bars = [b for row in bars for b in row]
        flat_curves = [p for row in curves for p in row]
        top = max([0] + [b["y"] for b in flat_bars] + [p["y"] for p in flat_curves])
    ys = nice_scale(0, max(top if top > 0 else 1, (s.get("yRange") or [0, 0])[1]))
    return {"xs": xs, "ys": ys, "curves": curves, "bars": bars}


def layout_dist(s: dict, g: dict) -> dict:
    """lib/charts-dist.ts:125-186 layoutDist()."""
    who = DIST_FN[s["kinds"][0]] if len(s["kinds"]) == 1 else "displot"
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    p = _plan(s)
    many = len(s["groups"]) > 1

    legend: list[dict] = []
    lx, row = g["x"], 0
    if many:
        for i, gr in enumerate(s["groups"]):
            w = 28 + 6 + c.tw(gr["label"]) + 22
            if lx + w - 22 > g["x"] + g["w"] and lx > g["x"]:
                lx, row = g["x"], row + 1
            legend.append({"x": lx, "row": row, "i": i})
            lx += w
    legend_h = (row + 1) * (size + 12) if many else 0
    head_h = legend_h + size + 10
    tick_w = max(c.tw(num_text(t)) for t in p["ys"]["ticks"])
    plot_l = g["x"] + tick_w + 16
    plot_r = g["x"] + g["w"] - math.ceil(c.tw(num_text(p["xs"]["max"])) / 2) - 6
    if plot_r - plot_l < 80:
        fail(who, "the figure is too narrow for its labels (raise width)")
    axis_h = size + 14 + (size + 10 if s["label"] else 0)
    c.h = g["height"] if g.get("height") is not None else 300 + head_h
    plot_t = g["y"] + head_h + math.ceil(size / 2) + 2
    plot_b = g["y"] + c.h - axis_h - 6
    if plot_b - plot_t < 100:
        fail(who, "the figure is too short; raise height")

    def x_of(v: float) -> float:
        return plot_l + (v - p["xs"]["min"]) / (p["xs"]["max"] - p["xs"]["min"]) * (plot_r - plot_l)

    def y_of(v: float) -> float:
        return plot_b - (v - p["ys"]["min"]) / (p["ys"]["max"] - p["ys"]["min"]) * (plot_b - plot_t)

    r1 = round1

    def pt(x: float, y: float) -> str:
        return f"{js_num(r1(x_of(x)))},{js_num(r1(y_of(y)))}"

    def stroke(i: int) -> dict:
        return {"stroke": TONES[i], "dash": DASH[i] or None}

    def fill_of(i: int) -> str:
        return TONES[i]

    for l in legend:
        cy = g["y"] + l["row"] * (size + 12) + max(9, math.ceil(size * 0.64))
        if "hist" in s["kinds"] and s["element"] == "bars":
            c.rect(l["x"], cy - 7, 22, 14, {"fill": fill_of(l["i"]), "op": 0.25, **stroke(l["i"]), "sw": 2})
        else:
            c.line(l["x"], cy, l["x"] + 22, cy, {**stroke(l["i"]), "sw": 2})
        c.text(s["groups"][l["i"]]["label"], l["x"] + 28, c.mid(cy), "start", "text")
    c.text(_y_name(s), plot_l - 4, g["y"] + legend_h + size + 2, "start", "muted", {"bold": True})
    for t in p["ys"]["ticks"]:
        c.line(plot_l - 6, y_of(t), plot_r, y_of(t), {"stroke": "text" if t == 0 else "border"})
        c.text(num_text(t), plot_l - 10, c.mid(y_of(t)), "end", "muted")
    for t in p["xs"]["ticks"]:
        c.line(x_of(t), plot_b, x_of(t), plot_b + 6, {"stroke": "border"})
        c.text(num_text(t), x_of(t), plot_b + size + 10, "middle", "muted")
    c.line(plot_l, plot_t, plot_l, plot_b, {"stroke": "border"})
    if s["label"]:
        c.text(s["label"], (plot_l + plot_r) / 2, plot_b + 2 * size + 22, "middle", "muted", {"bold": True})
    c.anchors.clear()

    for i, gr in enumerate(s["groups"]):
        of = gr.get("id") or f"#{i}"
        bars = p["bars"][i] if i < len(p["bars"]) else None
        op = 0.18 if many else 0.3
        if "hist" in s["kinds"] and bars:
            if s["element"] == "bars":
                for b in bars:
                    if b["y"] > 0:
                        c.path(f"M{pt(b['x0'], 0)} L{pt(b['x0'], b['y'])} L{pt(b['x1'], b['y'])} L{pt(b['x1'], 0)} Z", {"fill": fill_of(i), "op": op, **stroke(i), "sw": 2, "of": of})
            else:
                parts = []
                for k, b in enumerate(bars):
                    prev_y = bars[k - 1]["y"] if k else 0
                    parts.append(f"{'L' if k else 'M'}{pt(b['x0'], prev_y)} L{pt(b['x0'], b['y'])} L{pt(b['x1'], b['y'])}")
                d = " ".join(parts) + f" L{pt(bars[-1]['x1'], 0)}"
                c.path(d, {"fill": "none", **stroke(i), "sw": 2, "of": of})
        if "kde" in s["kinds"]:
            cv = p["curves"][i]
            d = " ".join(f"{'L' if k else 'M'}{pt(q['x'], q['y'])}" for k, q in enumerate(cv))
            if "hist" not in s["kinds"] or s["element"] == "step":
                c.path(f"{d} L{pt(cv[-1]['x'], 0)} L{pt(cv[0]['x'], 0)} Z", {"fill": fill_of(i), "op": 0.12 if many else 0.2, "of": of})
            c.path(d, {"fill": "none", **stroke(i), "sw": 2, "of": of})
        if "ecdf" in s["kinds"]:
            sorted_v = sorted(gr["values"])
            n = len(sorted_v)
            k = 1 if s["stat"] == "count" else 100 / n if s["stat"] == "percent" else 1 / n
            d = f"M{pt(p['xs']['min'], 0)}"
            for j, val in enumerate(sorted_v):
                d += f" L{pt(val, j * k)} L{pt(val, (j + 1) * k)}"
            c.path(f"{d} L{pt(p['xs']['max'], n * k)}", {"fill": "none", **stroke(i), "sw": 2, "of": of})
        if "rug" in s["kinds"]:
            for val in gr["values"]:
                c.line(x_of(val), plot_b - 1 - i * 10, x_of(val), plot_b - 9 - i * 10, {**stroke(i), "dash": None, "sw": 1.5, "of": of})
        if gr.get("id"):
            c.anchors.append({"id": gr["id"], "x": r1(plot_l), "y": r1(plot_t), "w": r1(plot_r - plot_l), "h": r1(plot_b - plot_t)})

    return c.done()


def dist_band(who: str, data, opts: dict | None, kind: str) -> dict:
    """lib/charts-dsl.ts's distBand() + the displot()/histplot()/.../rugplot() DSL wrappers."""
    opts = opts or {}
    spec = resolve_dist(who, data, opts, kind)
    alt = opts.get("alt") if opts.get("alt") is not None else dist_alt(spec)
    band: dict = {"type": "chart", "kind": "distplot", "spec": spec, "alt": alt, "ids": [g["id"] for g in spec["groups"] if g.get("id")]}
    band.update(common_chart_opts(who, id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
    return band
