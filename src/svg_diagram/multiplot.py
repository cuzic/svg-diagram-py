"""1:1 port of lib/charts-multi.ts's layoutMulti() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and lib/charts-dsl.ts's multiBand() — the seaborn-style
multi-variable plots (hist2d/kde2d/jointplot/pairplot), built on lib/stats.ts's kde2d() /
binCounts() / binIndex() and the histogram-binning helper also used by distplot.py.

multiTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as the
other chart kinds' *Texts() helpers.

Golden master: lib/charts-multi.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .charts_base import CHART_DASH as DASH
from .charts_base import CHART_TONES as TONES
from .charts_base import SHAPES, Canvas, ChartBand, check_ids, check_text, common_chart_opts, fail, finite_num, histogram_bins, ink_on_shade, marker_path, nice_scale, num_text
from .emit_common import round1
from .stats import bin_counts, bin_index, kde2d

LEVELS: list[float] = [0.1, 0.3, 0.5, 0.7, 0.9]


def _col(who: str, what: str, v) -> list[float]:
    """lib/charts-multi.ts:34-37 col()."""
    if not isinstance(v, list) or len(v) < 2:
        fail(who, f"{what} needs at least two values")
    return [finite_num(who, f"{what} value {i + 1}", q) for i, q in enumerate(v)]


def _groups_of(who: str, group: list[str] | None, n: int) -> dict:
    """lib/charts-multi.ts:38-45 groupsOf()."""
    if group is None:
        return {"gi": [0] * n, "names": []}
    if len(group) != n:
        fail(who, f"groups has {len(group)} labels for {n} rows")
    names: list[str] = []
    for gr in group:
        if gr not in names:
            names.append(gr)
    if len(names) > len(TONES):
        fail(who, f"at most {len(TONES)} groups (got {len(names)}: {', '.join(names)})")
    for gr in names:
        check_text(who, "a group label", gr)
    return {"gi": [names.index(gr) for gr in group], "names": names}


def resolve_multi(who: str, mode: str, data, opts: dict | None) -> dict:
    """lib/charts-multi.ts:46-66 resolveMulti()."""
    opts = opts or {}
    check_ids(who, [], opts.get("id"))
    base: dict = {"mode": mode, "xLabel": opts.get("xLabel") or "", "yLabel": opts.get("yLabel") or "", "corner": bool(opts.get("corner")), "ids": [], "x": [], "y": [], "vars": []}
    if opts.get("bins") is not None and not (isinstance(opts["bins"], int) and not isinstance(opts["bins"], bool) and opts["bins"] >= 1):
        fail(who, f"bins must be a whole number >= 1 (got {opts.get('bins')})")
    bins_kw = {"bins": opts["bins"]} if opts.get("bins") is not None else {}
    if mode == "pair":
        entries = list(data.items())
        if len(entries) < 2 or len(entries) > 6:
            fail(who, f"needs 2 to 6 variables (got {len(entries)})")
        variables = [{"name": check_text(who, "a variable name", name), "values": _col(who, f'"{name}"', v)} for name, v in entries]
        first = variables[0]
        if any(len(v["values"]) != len(first["values"]) for v in variables):
            fail(who, "every variable needs the same number of values")
        gn = _groups_of(who, opts.get("groups"), len(first["values"]))
        return {**base, **bins_kw, "vars": variables, "gi": gn["gi"], "names": gn["names"]}
    d = data
    if d is None or not isinstance(d, dict) or "x" not in d or "y" not in d:
        fail(who, "needs columns: {x: [..], y: [..]}")
    x, y = _col(who, "x", d["x"]), _col(who, "y", d["y"])
    if len(x) != len(y):
        fail(who, f"x has {len(x)} values and y has {len(y)}")
    if mode in ("hist2d", "kde2d"):
        gn = {"gi": [0] * len(x), "names": []}
    else:
        gn = _groups_of(who, d.get("group") or opts.get("groups"), len(x))
    return {**base, **bins_kw, "x": x, "y": y, "gi": gn["gi"], "names": gn["names"]}


def _ax(v: list[float]) -> dict:
    return nice_scale(min(v), max(v))


def _classes(v: list[float], bins: int | None) -> dict:
    return histogram_bins(v, bins if bins is not None else max(5, min(12, math.ceil(math.sqrt(len(v))))))


def multi_alt(s: dict) -> str:
    """lib/charts-multi.ts:70-74 multiAlt()."""

    def r(v: list[float]) -> str:
        return f"{num_text(min(v))}〜{num_text(max(v))}"

    if s["mode"] == "pair":
        parts = "、".join(f"{v['name']} {r(v['values'])}" for v in s["vars"])
        return f"散布図行列（{parts}、n={len(s['vars'][0]['values'])}）"
    name = "2次元ヒストグラム" if s["mode"] == "hist2d" else "2次元密度（KDE）" if s["mode"] == "kde2d" else "ジョイントプロット"
    return f"{name}（{s['xLabel'] or 'x'} {r(s['x'])}、{s['yLabel'] or 'y'} {r(s['y'])}、n={len(s['x'])}）"


def _density2d(s: dict) -> dict:
    """lib/charts-multi.ts:76-81 density2d()."""
    probe = kde2d(s["x"], s["y"], [0], [0])
    xs = nice_scale(min(s["x"]) - 1.5 * probe["bwx"], max(s["x"]) + 1.5 * probe["bwx"])
    ys = nice_scale(min(s["y"]) - 1.5 * probe["bwy"], max(s["y"]) + 1.5 * probe["bwy"])
    gx = [xs["min"] + (xs["max"] - xs["min"]) * i / 60 for i in range(61)]
    gy = [ys["min"] + (ys["max"] - ys["min"]) * j / 60 for j in range(61)]
    z = kde2d(s["x"], s["y"], gx, gy)["z"]
    return {"xs": xs, "ys": ys, "gx": gx, "gy": gy, "z": z, "max": max(max(row) for row in z)}


def _grid2d(s: dict) -> dict:
    """lib/charts-multi.ts:83-88 grid2d()."""
    bx, by = _classes(s["x"], s.get("bins")), _classes(s["y"], s.get("bins"))
    cells = [[0.0] * (len(bx["edges"]) - 1) for _ in range(len(by["edges"]) - 1)]
    for i, v in enumerate(s["x"]):
        row = cells[bin_index(s["y"][i], by["edges"])]
        at = bin_index(v, bx["edges"])
        row[at] += 1
    return {"bx": bx, "by": by, "cells": cells}


_r1 = round1


def layout_multi(s: dict, g: dict) -> dict:
    """lib/charts-multi.ts:107-297 layoutMulti()."""
    who = {"hist2d": "hist2d", "kde2d": "kde2d", "joint": "jointplot"}.get(s["mode"], "pairplot")
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    many = len(s["names"]) > 1

    def tone(i: int) -> str:
        return TONES[i]

    legend: list[dict] = []
    lx, row = g["x"], 0
    if many:
        for i, nm in enumerate(s["names"]):
            w = 20 + 6 + c.tw(nm) + 22
            if lx + w - 22 > g["x"] + g["w"] and lx > g["x"]:
                lx, row = g["x"], row + 1
            legend.append({"x": lx, "row": row, "i": i})
            lx += w
    legend_h = (row + 1) * (size + 12) if many else 0
    for l in legend:
        cy = g["y"] + l["row"] * (size + 12) + max(9, math.ceil(size * 0.64))
        c.path(marker_path(SHAPES[l["i"]], l["x"] + 7, cy, 5.5), {"fill": tone(l["i"]), "op": 0.85})
        c.text(s["names"][l["i"]], l["x"] + 20, c.mid(cy), "start", "text")

    marks: list[dict] = []

    def dots(sx, sy, xs: list[float], ys: list[float], r: float) -> None:
        for i, v in enumerate(xs):
            q = {"x": sx(v), "y": sy(ys[i])}
            k = s["gi"][i]
            c.path(marker_path(SHAPES[k], q["x"], q["y"], r), {"fill": tone(k), "op": 0.75, "stroke": "bg", "sw": 1})
            marks.append(q)

    def hist(values: list[float], edges: list[float], at, hmax: float, k: int) -> None:
        cnt = bin_counts(values, edges)
        if not many:
            for i, q in enumerate(cnt):
                if q <= 0:
                    continue
                h = q / hmax
                e0, e1 = edges[i], edges[i + 1]
                c.path(at(e0, h) + " " + at(e1, h).replace("M", "L", 1) + " " + at(e1, 0).replace("M", "L", 1) + " Z", {"fill": "accent", "op": 0.3, "stroke": "accent", "sw": 2})
        if many:
            d = ""
            for i, q in enumerate(cnt):
                h = q / hmax
                e0, e1 = edges[i], edges[i + 1]
                prev_h = cnt[i - 1] / hmax if i else 0
                d += f"{'L' if i else 'M'}{at(e0, prev_h)[1:]} L{at(e0, h)[1:]} L{at(e1, h)[1:]} "
            d += f"L{at(edges[-1], 0)[1:]}"
            c.path(d, {"fill": "none", "stroke": tone(k), "sw": 2, "dash": DASH[k] or None})

    def grid_and_ticks(rect: dict, xs: dict, ys: dict, xt: bool, yt: bool, y_right: bool = False):
        def sx(v: float) -> float:
            return rect["l"] + (v - xs["min"]) / (xs["max"] - xs["min"]) * (rect["r"] - rect["l"])

        def sy(v: float) -> float:
            return rect["b"] - (v - ys["min"]) / (ys["max"] - ys["min"]) * (rect["b"] - rect["t"])

        if xs:
            for t in xs["ticks"]:
                c.line(sx(t), rect["t"], sx(t), rect["b"], {"stroke": "border"})
                if xt:
                    c.text(num_text(t), sx(t), rect["b"] + size + 14, "middle", "muted")
        if ys:
            for t in ys["ticks"]:
                c.line(rect["l"], sy(t), rect["r"], sy(t), {"stroke": "border"})
                if yt:
                    c.text(num_text(t), rect["r"] + 8 if y_right else rect["l"] - 8, c.mid(sy(t)), "start" if y_right else "end", "muted")
        return sx, sy

    if s["mode"] == "kde2d":
        d = _density2d(s)
        tick_w = max(c.tw(num_text(t)) for t in d["ys"]["ticks"])
        head_h = size + 10 + (size + 10 if s["yLabel"] else 0)
        plot_l, plot_r = g["x"] + tick_w + 16, g["x"] + g["w"] - 110
        axis_h = size + 20 + (size + 10 if s["xLabel"] else 0)
        c.h = g["height"] if g.get("height") is not None else 360 + head_h
        plot_t, plot_b = g["y"] + head_h + math.ceil(size / 2), g["y"] + c.h - axis_h - 6
        if plot_r - plot_l < 120 or plot_b - plot_t < 120:
            fail(who, "the figure is too small (raise width / height)")

        def sx_k(v: float) -> float:
            return plot_l + (v - d["xs"]["min"]) / (d["xs"]["max"] - d["xs"]["min"]) * (plot_r - plot_l)

        def sy_k(v: float) -> float:
            return plot_b - (v - d["ys"]["min"]) / (d["ys"]["max"] - d["ys"]["min"]) * (plot_b - plot_t)

        def lvl(v: float) -> int:
            return len([f for f in LEVELS if v >= f * d["max"]])

        def op_of(level: int) -> float:
            return _r1(0.1 + 0.15 * level)

        dx, dy = (plot_r - plot_l) / 60, (plot_b - plot_t) / 60
        for j in range(61):
            i = 0
            zr, gyj = d["z"][j], d["gy"][j]
            while i <= 60:
                level = lvl(zr[i])
                k = i
                while k + 1 <= 60 and lvl(zr[k + 1]) == level:
                    k += 1
                if level > 0:
                    x0 = max(plot_l, sx_k(d["gx"][i]) - dx / 2)
                    x1 = min(plot_r, sx_k(d["gx"][k]) + dx / 2)
                    y0 = max(plot_t, sy_k(gyj) - dy / 2)
                    y1 = min(plot_b, sy_k(gyj) + dy / 2)
                    c.rect(_r1(x0), _r1(y0), _r1(x1 - x0) + 0.4, _r1(y1 - y0) + 1.2, {"fill": "accent", "op": op_of(level)})
                i = k + 1
        for t in d["xs"]["ticks"]:
            c.line(sx_k(t), plot_b, sx_k(t), plot_b + 6, {"stroke": "border"})
            c.text(num_text(t), sx_k(t), plot_b + size + 14, "middle", "muted")
        for t in d["ys"]["ticks"]:
            c.line(plot_l - 6, sy_k(t), plot_l, sy_k(t), {"stroke": "border"})
            c.text(num_text(t), plot_l - 10, c.mid(sy_k(t)), "end", "muted")
        for f in LEVELS:
            th = f * d["max"]
            segs: list[str] = []

            def P(i: int, j: int) -> dict:
                return {"x": sx_k(d["gx"][i]), "y": sy_k(d["gy"][j]), "v": d["z"][j][i]}

            def lerp(a: dict, b: dict) -> str:
                t = (th - a["v"]) / (b["v"] - a["v"])
                return f"{js_num_r1(a['x'] + (b['x'] - a['x']) * t)},{js_num_r1(a['y'] + (b['y'] - a['y']) * t)}"

            table: dict[int, list[tuple[int, int]]] = {1: [(3, 0)], 2: [(0, 1)], 3: [(3, 1)], 4: [(1, 2)], 5: [(3, 0), (1, 2)], 6: [(0, 2)], 7: [(3, 2)], 8: [(2, 3)], 9: [(0, 2)], 10: [(0, 1), (2, 3)], 11: [(1, 2)], 12: [(1, 3)], 13: [(0, 1)], 14: [(3, 0)]}
            for j in range(60):
                for i in range(60):
                    v0, v1, v2, v3 = P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)
                    code = (1 if v0["v"] >= th else 0) | (2 if v1["v"] >= th else 0) | (4 if v2["v"] >= th else 0) | (8 if v3["v"] >= th else 0)
                    e = [lambda: lerp(v0, v1), lambda: lerp(v1, v2), lambda: lerp(v3, v2), lambda: lerp(v0, v3)]
                    for a, b in table.get(code, []):
                        segs.append(f"M{e[a]()} L{e[b]()}")
            if segs:
                c.path(" ".join(segs), {"fill": "none", "stroke": "accent", "sw": 1.5})
        c.line(plot_l, plot_b, plot_r, plot_b, {"stroke": "text"})
        c.line(plot_l, plot_t, plot_l, plot_b, {"stroke": "text"})
        if s["yLabel"]:
            c.text(s["yLabel"], plot_l - 4, g["y"] + size + 2, "start", "muted", {"bold": True})
        if s["xLabel"]:
            c.text(s["xLabel"], (plot_l + plot_r) / 2, plot_b + 2 * size + 26, "middle", "muted", {"bold": True})
        lgx = plot_r + 24
        c.text("密度", lgx, plot_t + size, "start", "muted", {"bold": True})
        for k in range(6):
            c.rect(lgx, plot_t + size + 10 + k * 22, 22, 18, {"fill": "accent", "op": op_of(5 - k), "stroke": "border", "sw": 1})
        c.text("高", lgx + 30, c.mid(plot_t + size + 19), "start", "text")
        c.text("低", lgx + 30, c.mid(plot_t + size + 10 + 5 * 22 + 9), "start", "text")
        if len(s["x"]) <= 400:
            for i, xv in enumerate(s["x"]):
                c.path(marker_path("disc", sx_k(xv), sy_k(s["y"][i]), 2), {"fill": "text", "op": 0.5})
    elif s["mode"] == "hist2d":
        gd = _grid2d(s)
        bx, by, cells = gd["bx"], gd["by"], gd["cells"]
        xs = {"min": bx["edges"][0], "max": bx["edges"][-1], "ticks": bx["edges"]}
        ys = {"min": by["edges"][0], "max": by["edges"][-1], "ticks": by["edges"]}
        max_c = max(max(row) for row in cells)
        tick_w = max(c.tw(num_text(t)) for t in by["edges"])
        head_h = size + 10 + (size + 10 if s["yLabel"] else 0)
        plot_l, plot_r = g["x"] + tick_w + 16, g["x"] + g["w"] - 150
        axis_h = size + 20 + (size + 10 if s["xLabel"] else 0)
        c.h = g["height"] if g.get("height") is not None else 360 + head_h
        plot_t, plot_b = g["y"] + head_h + math.ceil(size / 2), g["y"] + c.h - axis_h - 6
        if plot_r - plot_l < 120 or plot_b - plot_t < 120:
            fail(who, "the figure is too small (raise width / height)")

        def sx_h(v: float) -> float:
            return plot_l + (v - xs["min"]) / (xs["max"] - xs["min"]) * (plot_r - plot_l)

        def sy_h(v: float) -> float:
            return plot_b - (v - ys["min"]) / (ys["max"] - ys["min"]) * (plot_b - plot_t)

        def thin(ticks: list[float], px, size_fn) -> set[float]:
            w = max(size_fn(t) for t in ticks) + 10
            pitch = abs(px(ticks[1]) - px(ticks[0]))
            k = max(1, math.ceil(w / pitch))
            return {t for i, t in enumerate(ticks) if i % k == 0}

        show_x = thin(xs["ticks"], sx_h, lambda t: c.tw(num_text(t)))
        show_y = thin(ys["ticks"], sy_h, lambda _t: size + 2)
        for t in xs["ticks"]:
            if t in show_x:
                c.text(num_text(t), sx_h(t), plot_b + size + 14, "middle", "muted")
        for t in ys["ticks"]:
            if t in show_y:
                c.text(num_text(t), plot_l - 8, c.mid(sy_h(t)), "end", "muted")
        if s["yLabel"]:
            c.text(s["yLabel"], plot_l - 4, g["y"] + size + 2, "start", "muted", {"bold": True})
        if s["xLabel"]:
            c.text(s["xLabel"], (plot_l + plot_r) / 2, plot_b + 2 * size + 26, "middle", "muted", {"bold": True})
        for j, rw in enumerate(cells):
            for i, q in enumerate(rw):
                if q <= 0:
                    continue
                x0, x1 = sx_h(bx["edges"][i]), sx_h(bx["edges"][i + 1])
                y1, y0 = sy_h(by["edges"][j]), sy_h(by["edges"][j + 1])
                op = _r1(0.12 + 0.78 * q / max_c)
                ink = ink_on_shade(op)
                host = c.rect(_r1(x0), _r1(y0), _r1(x1 - x0), _r1(y1 - y0), {"fill": "accent", "op": op, "stroke": "bg", "sw": 1, "solid": f"the cell {i + 1},{j + 1}"})
                t = num_text(q)
                if c.tw(t, True) + 6 <= x1 - x0 and size + 4 <= y1 - y0:
                    c.text(t, (x0 + x1) / 2, c.mid((y0 + y1) / 2), "middle", ink, {"bold": True, "host": host, "on": {"fill": "accent", "op": op, "ink": ink}})
        c.line(plot_l, plot_b, plot_r, plot_b, {"stroke": "text"})
        c.line(plot_l, plot_t, plot_l, plot_b, {"stroke": "text"})
        lgx, sw = plot_r + 24, 22
        c.text("件数", lgx, plot_t + size, "start", "muted", {"bold": True})
        for k in range(5):
            c.rect(lgx, plot_t + size + 10 + k * 26, sw, 22, {"fill": "accent", "op": _r1(0.12 + 0.78 * (4 - k) / 4), "stroke": "border", "sw": 1})
        c.text(num_text(max_c), lgx + sw + 8, c.mid(plot_t + size + 21), "start", "text")
        c.text("0", lgx + sw + 8, c.mid(plot_t + size + 10 + 4 * 26 + 11), "start", "text")
    elif s["mode"] == "joint":
        xs, ys = _ax(s["x"]), _ax(s["y"])
        bx, by = _classes(s["x"], s.get("bins")), _classes(s["y"], s.get("bins"))
        tick_w = max(c.tw(num_text(t)) for t in ys["ticks"])
        head_h = legend_h + (size + 10 if s["yLabel"] else 0)
        mh = 70
        main_l, main_r = g["x"] + tick_w + 16, g["x"] + g["w"] - mh - 18
        axis_h = size + 14 + (size + 10 if s["xLabel"] else 0)
        c.h = g["height"] if g.get("height") is not None else 400 + head_h
        main_t, main_b = g["y"] + head_h + mh + 8, g["y"] + c.h - axis_h - 6
        if main_r - main_l < 120 or main_b - main_t < 120:
            fail(who, "the figure is too small (raise width / height)")
        if s["yLabel"]:
            c.text(s["yLabel"], g["x"], g["y"] + legend_h + size + 2, "start", "muted", {"bold": True})
        sx_j, sy_j = grid_and_ticks({"l": main_l, "r": main_r, "t": main_t, "b": main_b}, xs, ys, True, True)
        c.line(main_l, main_b, main_r, main_b, {"stroke": "text"})
        c.line(main_l, main_t, main_l, main_b, {"stroke": "text"})
        if s["xLabel"]:
            c.text(s["xLabel"], (main_l + main_r) / 2, main_b + 2 * size + 26, "middle", "muted", {"bold": True})
        dots(sx_j, sy_j, s["x"], s["y"], 3.5)
        top, top_b, right = g["y"] + head_h, main_t - 8, main_r + 8

        def pergroup(v: list[float], edges: list[float], k: int) -> list[float]:
            return bin_counts([q for i, q in enumerate(v) if s["gi"][i] == k], edges)

        kk = max(1, len(s["names"]))
        for vals, edges, horizontal in ((s["x"], bx["edges"], False), (s["y"], by["edges"], True)):
            hmax = max(max(pergroup(vals, edges, k)) for k in range(kk))
            for k in range(kk):
                v = [q for i, q in enumerate(vals) if s["gi"][i] == k]
                if not horizontal:
                    hist(v, edges, lambda e, h: f"M{js_num_r1(sx_j(e))},{js_num_r1(top_b - h * (top_b - top))}", hmax, k)
                else:
                    hist(v, edges, lambda e, h: f"M{js_num_r1(right + h * mh)},{js_num_r1(sy_j(e))}", hmax, k)
        for m in marks:
            c.marks.append({"x": m["x"] - 4, "y": m["y"] - 4, "w": 8, "h": 8})
    else:
        k_n = len(s["vars"])
        scales = [_ax(v["values"]) for v in s["vars"]]
        bins_list = [_classes(v["values"], s.get("bins")) for v in s["vars"]]
        name_w = min(max(c.tw(v["name"], True) for v in s["vars"]) + 14, g["w"] * 0.22)
        tick_w = max(c.tw(num_text(t)) for sc in scales for t in sc["ticks"])
        left = g["x"] + name_w + tick_w + 14
        cell = math.floor((g["x"] + g["w"] - left - tick_w - 14) / k_n)
        if cell < 70:
            fail(who, "the panels are too small (raise width, or use fewer variables)")
        top = g["y"] + legend_h + math.ceil(size / 2) + 6
        pad_x, pad_y, axis_h = math.ceil(tick_w) + 6, size + 8, size + 14
        c.h = g["height"] if g.get("height") is not None else top - g["y"] + k_n * cell + axis_h + 10
        if g.get("height") is not None and g["height"] < top - g["y"] + k_n * 70 + axis_h:
            fail(who, "the figure is too short; raise height")
        side = min(cell, math.floor((c.h - (top - g["y"]) - axis_h - 10) / k_n))
        for i in range(k_n):
            t, b = top + i * side, top + i * side + side - pad_y
            wrap = c.wrap(s["vars"][i]["name"], name_w - 14, True)
            c.lines(wrap, left - tick_w - 12, c.mid(t + (b - t) / 2) - (len(wrap) - 1) * c.line_h() / 2, "end", "text", {"bold": True})
            for j in range(k_n):
                if s["corner"] and j > i:
                    continue
                l, r = left + j * cell, left + j * cell + cell - pad_x
                if i == j:
                    edges = bins_list[i]["edges"]
                    kk = max(1, len(s["names"]))
                    vals, sci = s["vars"][i]["values"], scales[i]
                    per = [bin_counts([v for n, v in enumerate(vals) if s["gi"][n] == q], edges) for q in range(kk)]
                    hmax = max(c_ for row in per for c_ in row)

                    def sx_d(v: float, l=l, r=r, sci=sci) -> float:
                        return l + (v - sci["min"]) / (sci["max"] - sci["min"]) * (r - l)

                    for tk in sci["ticks"]:
                        c.line(sx_d(tk), t, sx_d(tk), b, {"stroke": "border"})
                    for q in range(kk):
                        hist([v for n, v in enumerate(vals) if s["gi"][n] == q], edges, lambda e, h, sx_d=sx_d, t=t, b=b: f"M{js_num_r1(sx_d(e))},{js_num_r1(b - h * (b - t) * 0.92)}", hmax, q)
                    c.line(l, b, r, b, {"stroke": "text"})
                else:
                    sx_o, sy_o = grid_and_ticks({"l": l, "r": r, "t": t, "b": b}, scales[j], scales[i], False, False)
                    c.line(l, b, r, b, {"stroke": "border"})
                    c.line(l, t, l, b, {"stroke": "border"})
                    dots(sx_o, sy_o, s["vars"][j]["values"], s["vars"][i]["values"], 2.5)
        for j in range(k_n):
            l, r = left + j * cell, left + j * cell + cell - pad_x
            last = top + (k_n - 1) * side + side - pad_y
            scj = scales[j]
            for tk in scj["ticks"]:
                c.text(num_text(tk), l + (tk - scj["min"]) / (scj["max"] - scj["min"]) * (r - l), last + size + 14, "middle", "muted")
            c.text(s["vars"][j]["name"], (l + r) / 2, last + 2 * size + 20, "middle", "text", {"bold": True})
        c.h = max(c.h, top - g["y"] + k_n * side + 2 * size + 32)
        for i in range(k_n):
            t, b = top + i * side, top + i * side + side - pad_y
            sci = scales[i]

            def sy_lbl(v: float, b=b, t=t, sci=sci) -> float:
                return b - (v - sci["min"]) / (sci["max"] - sci["min"]) * (b - t)

            if i == 0 and k_n > 1 and not s["corner"]:
                r = left + (k_n - 1) * cell + cell - pad_x
                for tk in scales[0]["ticks"]:
                    c.text(num_text(tk), r + 8, c.mid(sy_lbl(tk)), "start", "muted")
            elif i > 0:
                for tk in sci["ticks"]:
                    c.text(num_text(tk), left - 8, c.mid(sy_lbl(tk)), "end", "muted")
        for m in marks:
            c.marks.append({"x": m["x"] - 3, "y": m["y"] - 3, "w": 6, "h": 6})

    return c.done()


def js_num_r1(v: float) -> str:
    from .emit_common import js_num

    return js_num(_r1(v))


def multi_band(who: str, mode: str, data: dict, opts: dict | None = None) -> ChartBand:
    """lib/charts-dsl.ts's multiBand() + the hist2d()/jointplot()/kde2d()/pairplot() DSL
    wrappers."""
    opts = opts or {}
    spec = resolve_multi(who, mode, data, opts)
    opt_alt = opts.get("alt")
    alt = opt_alt if opt_alt is not None else multi_alt(spec)
    return ChartBand(kind="multiplot", spec=spec, alt=alt, **common_chart_opts(who, id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
