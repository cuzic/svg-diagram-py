"""1:1 port of lib/charts-reg.ts's layoutReg() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and lib/charts-dsl.ts's regBand() — the seaborn-style
regression plots (regplot/residplot), built on lib/stats.ts's polyFit()/lowessFit()/meanOf().

regTexts()/regAxes() (Node's text-measurement-batching / facet-axis-sharing helpers) are not
ported — same reasoning as the other chart kinds' *Texts() helpers.

Golden master: lib/charts-reg.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .charts_base import CHART_DASH as DASH
from .charts_base import CHART_TONES as TONES
from .charts_base import SHAPES, Canvas, ChartBand, _to_precision, check_ids, check_range, check_text, common_chart_opts, fail, finite_num, marker_path, nice_scale, num_text
from .emit_common import js_num, round1
from .stats import lowess_fit, mean_of, poly_fit


def resolve_reg(who: str, resid: bool, data: dict, opts: dict | None) -> dict:
    """lib/charts-reg.ts:39-66 resolveReg()."""
    opts = opts or {}
    check_ids(who, [], opts.get("id"))
    if data is None or not isinstance(data, dict) or "x" not in data or "y" not in data:
        fail(who, "needs columns: {x: [..], y: [..]}")
    order = opts.get("order") if opts.get("order") is not None else 1
    lowess = bool(opts.get("lowess"))
    frac = opts.get("frac") if opts.get("frac") is not None else 2 / 3
    if not (0 < frac <= 1):
        fail(who, f"frac must be a number in (0, 1] (got {opts.get('frac')})")
    if lowess and not resid and opts.get("stats"):
        fail(who, "stats (an equation and R²) needs a polynomial fit: it is not defined for lowess")
    if lowess and not resid and opts.get("order") is not None:
        fail(who, "order and lowess are two ways to draw the curve: give one")
    if order not in (1, 2, 3):
        fail(who, f"order must be 1, 2 or 3 (got {opts.get('order')})")

    def num(what: str, v) -> list[float]:
        if not isinstance(v, list) or len(v) < 2:
            fail(who, f"{what} needs at least two values")
        return [finite_num(who, f"{what} value {i + 1}", q) for i, q in enumerate(v)]

    x, y = num("x", data["x"]), num("y", data["y"])
    if len(x) != len(y):
        fail(who, f"x has {len(x)} values and y has {len(y)}")
    labels = data.get("group") if data.get("group") is not None else opts.get("groups")
    if labels is not None and len(labels) != len(x):
        fail(who, f"groups has {len(labels)} labels for {len(x)} rows")
    if labels is None:
        names = [""]
    else:
        names = []
        for lab in labels:
            if lab not in names:
                names.append(lab)
    if len(names) > len(TONES):
        fail(who, f"at most {len(TONES)} groups (got {len(names)}: {', '.join(names)})")
    if labels is not None:
        for n in names:
            check_text(who, "a group label", n)
    groups = []
    for name in names:
        idx = [i for i in range(len(x)) if labels is None or labels[i] == name]
        gx, gy = [x[i] for i in idx], [y[i] for i in idx]
        label = f'"{name}"' if name else "the data"
        if len(gx) < order + 2:
            fail(who, f"{label}: a fit of order {order} needs at least {order + 2} points (got {len(gx)})")
        if len(set(gx)) < order + 1:
            fail(who, f"{label}: the x values need at least {order + 1} different values for a fit of order {order}")
        fit = poly_fit(gx, gy, order)
        group: dict = {"name": name, "x": gx, "y": gy, "fit": fit}
        if lowess:
            smooth_values = [v - fit.at(gx[i]) for i, v in enumerate(gy)] if resid else gy
            group["smooth"] = lowess_fit(gx, smooth_values, frac)
        groups.append(group)

    spec: dict = {"resid": resid, "xLabel": opts.get("xLabel") or "", "yLabel": opts.get("yLabel") or "", "order": order, "band": opts.get("band") if opts.get("band") is not None else True, "stats": bool(opts.get("stats")), "lowess": lowess, "groups": groups}
    x_range, y_range = check_range(who, opts, "xRange"), check_range(who, opts, "yRange")
    if x_range:
        spec["xRange"] = x_range
    if y_range:
        spec["yRange"] = y_range
    return spec


def _sgn(v: float) -> str:
    return f"{'−' if v < 0 else '+'} {num_text(abs(_to_precision(v, 3)))}"


def _stat_text(s: dict, fit, xs: list[float], ys: list[float]) -> str:
    """lib/charts-reg.ts:68-75 statText()."""
    r2 = f"R² = {num_text(_to_precision(fit.r2, 2))}"
    if s["order"] > 1 or s["resid"]:
        return r2
    mx, my = mean_of(xs), mean_of(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (ys[i] - my) for i, x in enumerate(xs)) / sxx
    icpt = my - slope * mx
    return f"y = {num_text(_to_precision(slope, 3))}x {_sgn(icpt)}（{r2}）"


def _legend_text(s: dict, g: dict) -> str:
    sep = " " if (g["name"] and s["stats"]) else ""
    return f"{g['name']}{sep}{_stat_text(s, g['fit'], g['x'], g['y']) if s['stats'] else ''}"


def reg_alt(s: dict) -> str:
    """lib/charts-reg.ts:78-80 regAlt()."""
    kind = ("残差プロットとLOWESS平滑線" if s["lowess"] else "残差プロット") if s["resid"] else ("散布図とLOWESS平滑線" if s["lowess"] else "散布図と回帰直線" if s["order"] == 1 else f"散布図と{s['order']}次の回帰曲線")
    groups_txt = "、".join(f"{(g['name'] + ' ') if g['name'] else ''}n={len(g['x'])} R²={num_text(_to_precision(g['fit'].r2, 2))}" for g in s["groups"])
    return f"{kind}（{s['xLabel'] or 'x'}・{s['yLabel'] or 'y'}）: {groups_txt}"


def _curves(s: dict, xs: dict) -> list[dict]:
    """lib/charts-reg.ts:82-90 curves()."""
    out = []
    for g in s["groups"]:
        lo, hi = min(g["x"]), max(g["x"])
        grid = [lo + (hi - lo) * i / 60 for i in range(61)]
        smooth = g.get("smooth")
        if smooth and not s["resid"]:
            line = [{"x": x, "y": smooth(x)} for x in grid]
            out.append({"fit": line, "up": line, "dn": line, "pts": [{"x": x, "y": g["y"][i]} for i, x in enumerate(g["x"])], "xs": xs})
            continue
        fit = g["fit"]

        def fit_y(x: float, resid=s["resid"], smooth=smooth) -> float:
            return (smooth(x) if smooth else 0) if resid else fit.at(x)

        half_of = (lambda x: fit.half(x) if fit.half else 0)
        out.append({
            "fit": [{"x": x, "y": fit_y(x)} for x in grid],
            "up": [{"x": x, "y": fit.at(x) + half_of(x)} for x in grid],
            "dn": [{"x": x, "y": fit.at(x) - half_of(x)} for x in grid],
            "pts": [{"x": x, "y": (g["y"][i] - fit.at(x)) if s["resid"] else g["y"][i]} for i, x in enumerate(g["x"])],
            "xs": xs,
        })
    return out


def _scales(s: dict) -> dict:
    """lib/charts-reg.ts:91-95 scales()."""
    all_x = [v for g in s["groups"] for v in g["x"]]
    x_range = s.get("xRange")
    xs = nice_scale(min(all_x + ([x_range[0]] if x_range else [])), max(all_x + ([x_range[1]] if x_range else [])))
    cv = _curves(s, xs)
    ys_all: list[float] = []
    for i, _g in enumerate(s["groups"]):
        ci = cv[i]
        ys_all.extend(p["y"] for p in ci["pts"])
        if s["resid"]:
            ys_all.append(0)
            if s["lowess"]:
                ys_all.extend(p["y"] for p in ci["fit"])
        elif s["band"]:
            ys_all.extend(p["y"] for p in ci["up"])
            ys_all.extend(p["y"] for p in ci["dn"])
        else:
            ys_all.extend(p["y"] for p in ci["fit"])
    top = max(abs(v) for v in ys_all)
    y_range = s.get("yRange")
    if s["resid"]:
        yscale = nice_scale(min(-top, y_range[0] if y_range else 0), max(top, y_range[1] if y_range else 0))
    else:
        yscale = nice_scale(min(ys_all + ([y_range[0]] if y_range else [])), max(ys_all + ([y_range[1]] if y_range else [])))
    return {"xs": xs, "ys": yscale, "cv": cv}


def layout_reg(s: dict, g: dict) -> dict:
    """lib/charts-reg.ts:109-148 layoutReg()."""
    who = "residplot" if s["resid"] else "regplot"
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])

    r1 = round1

    sc = _scales(s)

    def tone(i: int) -> str:
        return TONES[i]

    entries = [{"i": i, "text": _legend_text(s, gr)} for i, gr in enumerate(s["groups"])]
    entries = [e for e in entries if e["text"] and (len(s["groups"]) > 1 or s["stats"])]
    legend: list[dict] = []
    lx, row = g["x"], 0
    for e in entries:
        w = 30 + 6 + c.tw(e["text"]) + 22
        if lx + w - 22 > g["x"] + g["w"] and lx > g["x"]:
            lx, row = g["x"], row + 1
        legend.append({"x": lx, "row": row, "i": e["i"], "text": e["text"]})
        lx += w
    legend_h = (row + 1) * (size + 12) if entries else 0
    y_name = s["yLabel"] or ("残差" if s["resid"] else "")
    head_h = legend_h + (size + 10 if y_name else 0)
    tick_w = max(c.tw(num_text(t)) for t in sc["ys"]["ticks"])
    plot_l = g["x"] + tick_w + 16
    plot_r = g["x"] + g["w"] - math.ceil(c.tw(num_text(sc["xs"]["max"])) / 2) - 6
    axis_h = size + 20 + (size + 10 if s["xLabel"] else 0)
    if plot_r - plot_l < 80:
        fail(who, "the figure is too narrow for its labels (raise width)")
    c.h = g["height"] if g.get("height") is not None else 340 + head_h
    plot_t = g["y"] + head_h + math.ceil(size / 2) + 2
    plot_b = g["y"] + c.h - axis_h - 6
    if plot_b - plot_t < 100:
        fail(who, "the figure is too short; raise height")

    def x_of(v: float) -> float:
        return plot_l + (v - sc["xs"]["min"]) / (sc["xs"]["max"] - sc["xs"]["min"]) * (plot_r - plot_l)

    def y_of(v: float) -> float:
        return plot_b - (v - sc["ys"]["min"]) / (sc["ys"]["max"] - sc["ys"]["min"]) * (plot_b - plot_t)

    def pt(p: dict) -> str:
        return f"{js_num(r1(x_of(p['x'])))},{js_num(r1(y_of(p['y'])))}"

    def line(ps: list[dict]) -> str:
        return " ".join(f"{'L' if k else 'M'}{pt(p)}" for k, p in enumerate(ps))

    for l in legend:
        cy = g["y"] + l["row"] * (size + 12) + max(9, math.ceil(size * 0.64))
        c.path(marker_path(SHAPES[l["i"]] if l["i"] < len(SHAPES) else "disc", l["x"] + 5, cy, 4.5), {"fill": tone(l["i"]), "op": 0.8})
        c.line(l["x"] + 12, cy, l["x"] + 30, cy, {"stroke": tone(l["i"]), "sw": 2, "dash": DASH[l["i"]] or None})
        c.text(l["text"], l["x"] + 36, c.mid(cy), "start", "text")
    if y_name:
        c.text(y_name, plot_l - 4, g["y"] + legend_h + size + 2, "start", "muted", {"bold": True})
    for t in sc["ys"]["ticks"]:
        c.line(plot_l - 6, y_of(t), plot_r, y_of(t), {"stroke": "text" if (t == 0 and s["resid"]) else "border"})
        c.text(num_text(t), plot_l - 10, c.mid(y_of(t)), "end", "muted")
    for t in sc["xs"]["ticks"]:
        c.line(x_of(t), plot_b, x_of(t), plot_b + 6, {"stroke": "border"})
        c.text(num_text(t), x_of(t), plot_b + size + 14, "middle", "muted")
    c.line(plot_l, plot_t, plot_l, plot_b, {"stroke": "border"})
    c.line(plot_l, plot_b, plot_r, plot_b, {"stroke": "border" if s["resid"] else "text"})
    if s["xLabel"]:
        c.text(s["xLabel"], (plot_l + plot_r) / 2, plot_b + 2 * size + 26, "middle", "muted", {"bold": True})
    marks: list[dict] = []
    for i in range(len(s["groups"])):
        cv = sc["cv"][i]
        if s["band"] and not s["resid"] and cv["up"] and cv["fit"] and cv["up"][0]["y"] != cv["fit"][0]["y"]:
            c.path(f"{line(cv['up'])} L{line(list(reversed(cv['dn'])))[1:]} Z", {"fill": tone(i), "op": 0.14})
        for p in cv["pts"]:
            c.path(marker_path(SHAPES[i] if i < len(SHAPES) else "disc", x_of(p["x"]), y_of(p["y"]), 3.5), {"fill": tone(i), "op": 0.75, "stroke": "bg", "sw": 1})
            marks.append({"x": x_of(p["x"]), "y": y_of(p["y"])})
        if not s["resid"] or s["lowess"]:
            c.path(line(cv["fit"]), {"fill": "none", "stroke": tone(i), "sw": 2.5, "dash": DASH[i] or None})
    for m in marks:
        c.marks.append({"x": m["x"] - 4, "y": m["y"] - 4, "w": 8, "h": 8})
    if s["resid"]:
        c.line(plot_l, y_of(0), plot_r, y_of(0), {"stroke": "text", "sw": 2, "dash": "6,4"})
    return c.done()


def reg_band(who: str, resid: bool, data: dict, opts: dict | None = None) -> ChartBand:
    """lib/charts-dsl.ts's regBand() + the regplot()/residplot() DSL wrappers."""
    opts = opts or {}
    spec = resolve_reg(who, resid, data, opts)
    opt_alt = opts.get("alt")
    alt = opt_alt if opt_alt is not None else reg_alt(spec)
    return ChartBand(kind="regplot", spec=spec, alt=alt, **common_chart_opts(who, id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
