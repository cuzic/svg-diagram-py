"""1:1 port of lib/charts-cat.ts's layoutCat() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and lib/charts-dsl.ts's catBand() — the seaborn-style
categorical plots (boxplot/violinplot/stripplot/swarmplot/pointplot/barplot/catplot), built on
lib/stats.ts's pure statistics (box_stats/error_bar/kde/swarm_offsets, ported in stats.py).

catTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as the
other chart kinds' *Texts() helpers.

Golden master: lib/charts-cat.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import json
import math

from .charts_base import SHAPES, Canvas, ChartBand, check_ids, check_text, common_chart_opts, fail, finite_num, marker_path, nice_scale, num_text, shade_ops
from .emit_common import js_num, round1
from .stats import box_stats, error_bar, kde, mean_of, swarm_offsets

CatKind = str
KINDS: list[str] = ["box", "violin", "strip", "swarm", "point", "bar"]
FN: dict[str, str] = {"box": "boxplot", "violin": "violinplot", "strip": "stripplot", "swarm": "swarmplot", "point": "pointplot", "bar": "barplot"}
NAME: dict[str, str] = {"box": "箱ひげ図", "violin": "バイオリンプロット", "strip": "ストリッププロット", "swarm": "スウォームプロット", "point": "ポイントプロット", "bar": "棒グラフ（誤差つき）"}

MAX_HUES, MAX_GROUPS = 4, 24


def resolve_cat(who: str, data, opts: dict | None, default_kind: str = "box") -> dict:
    """lib/charts-cat.ts:43-77 resolveCat()."""
    opts = opts or {}
    lst = [{"label": label, "values": list(values)} for label, values in data.items()] if isinstance(data, dict) else [dict(g) for g in data]
    if len(lst) == 0:
        fail(who, "needs at least one group")
    if len(lst) > MAX_GROUPS:
        fail(who, f"{len(lst)} groups are too many for one figure (at most {MAX_GROUPS})")
    check_ids(who, [g.get("id") for g in lst], opts.get("id"))
    kind_opt = opts.get("kind")
    kinds = [default_kind] if kind_opt is None else (list(kind_opt) if isinstance(kind_opt, list) else [kind_opt])
    if len(kinds) == 0 or any(k not in KINDS for k in kinds):
        fail(who, f"kind must be {' / '.join(KINDS)} (or a list of them; got {json.dumps(kind_opt)})")
    if len(set(kinds)) != len(kinds):
        fail(who, "each kind may appear once in kind")
    if "strip" in kinds and "swarm" in kinds:
        fail(who, "strip and swarm both place every point: use one of them")
    if "bar" in kinds and "point" in kinds:
        fail(who, "bar and point both show the mean: use one of them")
    dir_ = opts.get("dir", "v") or "v"
    error = opts.get("error") or "ci"
    values_opt = opts.get("values")
    if values_opt is None:
        values_opt = "mean" if "bar" in kinds else "none"
    scale = opts.get("scale") or "area"
    if dir_ not in ("v", "h"):
        fail(who, f"dir must be 'v' or 'h' (got {opts.get('dir')!r})")
    if error not in ("ci", "sd", "se", "range", "none"):
        fail(who, f"error must be ci / sd / se / range / none (got {opts.get('error')!r})")
    if values_opt not in ("median", "mean", "none"):
        fail(who, f"values must be median / mean / none (got {opts.get('values')!r})")
    if scale not in ("area", "width"):
        fail(who, f"scale must be area or width (got {opts.get('scale')!r})")
    has_hue = any(g.get("hues") is not None for g in lst)
    if has_hue and any(g.get("hues") is None for g in lst):
        fail(who, "when one group has hues, every group needs them (give `hues` in each, not `values`)")
    if any(g.get("hues") is not None and g.get("values") is not None for g in lst):
        fail(who, "a group has either values or hues, not both")
    hues: list[str] = []
    for g in lst:
        for h in g.get("hues") or []:
            name = check_text(who, "a hue name", h["name"])
            if name not in hues:
                hues.append(name)
    if len(hues) > MAX_HUES:
        fail(who, f"at most {MAX_HUES} hues (got {len(hues)}: {', '.join(hues)})")

    def series(g: dict, name: str, vs) -> dict | None:
        if vs is None or len(vs) == 0:
            return None
        what = f"\"{g['label']}\"" + (f' / "{name}"' if name else "")
        v = [finite_num(who, f"{what} value {i + 1}", x) for i, x in enumerate(vs)]
        if "violin" in kinds and (len(v) < 2 or min(v) == max(v)):
            fail(who, f"{what}: a violin needs at least two different values (use box / strip for a group this small)")
        out: dict = {"name": name, "values": v, "n": len(v), "mean": mean_of(v), "box": box_stats(v)}
        if any(k in ("point", "bar") for k in kinds):
            e = error_bar(v, error)
            if e:
                out["err"] = list(e)
        return out

    groups = []
    for i, g in enumerate(lst):
        label = check_text(who, f"group {i + 1}'s label", g["label"])
        if has_hue:
            s_list = [series(g, h, next((x["values"] for x in (g.get("hues") or []) if x["name"] == h), None)) for h in hues]
        else:
            s_list = [series(g, "", g.get("values"))]
        if all(x is None for x in s_list):
            fail(who, f'"{label}" has no values')
        group: dict = {"label": label, "series": s_list}
        if g.get("id") is not None:
            group["id"] = g["id"]
        groups.append(group)
    return {
        "groups": groups, "hues": hues, "kinds": kinds, "dir": dir_, "label": opts.get("label") or "",
        "unit": opts.get("unit") or "", "error": error, "values": values_opt, "counts": bool(opts.get("counts")), "scale": scale,
    }


def _count_text(g: dict) -> str:
    return "n = " + " / ".join(str(x["n"]) for x in g["series"] if x is not None)


def _value_at(s: dict, x: dict) -> float:
    return x["mean"] if s["values"] == "mean" else x["box"].median


def cat_alt(s: dict) -> str:
    """lib/charts-cat.ts:82-86 catAlt()."""

    def stat(x: dict) -> str:
        if "bar" in s["kinds"] or "point" in s["kinds"]:
            err_txt = ""
            if x.get("err"):
                kind_txt = {"ci": "95%信頼区間", "sd": "±標準偏差", "se": "±標準誤差", "range": "範囲"}[s["error"]]
                err_txt = f"（{kind_txt} {num_text(x['err'][0])}〜{num_text(x['err'][1])}）"
            return f"平均 {num_text(x['mean'])}{s['unit']}{err_txt}"
        b = x["box"]
        return f"中央値 {num_text(b.median)}{s['unit']}（四分位 {num_text(b.q1)}〜{num_text(b.q3)}）"

    kinds_txt = "＋".join(NAME[k] for k in s["kinds"])
    label_txt = f"（{s['label']}）" if s["label"] else ""
    groups_txt = "、".join(
        "、".join(f"{g['label']}{(' ' + x['name']) if x['name'] else ''} n={x['n']} {stat(x)}" for x in g["series"] if x is not None)
        for g in s["groups"]
    )
    return f"{kinds_txt}{label_txt}: {groups_txt}"


_r1 = round1


def layout_cat(s: dict, g: dict) -> dict:
    """lib/charts-cat.ts:112-265 layoutCat()."""
    who = FN[s["kinds"][0]] if len(s["kinds"]) == 1 else "catplot"
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    lh = c.line_h()
    v = s["dir"] == "v"
    n = len(s["groups"])
    h_count = max(1, len(s["hues"]))
    rect_kind = any(k in ("box", "violin", "bar") for k in s["kinds"])
    all_vals = [val for gr in s["groups"] for x in gr["series"] if x for val in (x["box"].min, x["box"].max, *(x.get("err") or []))]
    lo_extra = [0] if "bar" in s["kinds"] else []

    def tick(t: float) -> str:
        return num_text(t)

    sc = nice_scale(min(all_vals + lo_extra), max(all_vals + lo_extra))

    legend: list[dict] = []
    lx, row = g["x"], 0
    for i, h in enumerate(s["hues"]):
        w = 14 + 6 + c.tw(h) + 22
        if lx + w - 22 > g["x"] + g["w"] and lx > g["x"]:
            lx, row = g["x"], row + 1
        legend.append({"x": lx, "row": row, "i": i})
        lx += w
    legend_h = (row + 1) * (size + 12) if s["hues"] else 0
    name_h = size + 10 if (v and s["label"]) else 0
    head_h = legend_h + name_h

    tick_w = max(c.tw(tick(t)) for t in sc["ticks"])
    label_w = 0.0
    if not v:
        label_w = min(max(max(c.tw(gr["label"], True), c.tw(_count_text(gr)) if s["counts"] else 0) for gr in s["groups"]) + 14, g["w"] * 0.3)
    plot_l = (g["x"] + tick_w + 16) if v else (g["x"] + label_w + 8)
    plot_r = g["x"] + g["w"] - (8 if v else math.ceil(c.tw(tick(sc["ticks"][-1])) / 2) + 6)
    if plot_r - plot_l < 80:
        fail(who, "the figure is too narrow for its labels (raise width, or shorten the group names)")
    slot_v = (plot_r - plot_l) / n
    wrapped = [c.wrap(gr["label"], (slot_v - 8) if v else (label_w - 14), True) for gr in s["groups"]]
    count_line = 1 if s["counts"] else 0
    cat_h = (max(len(l) + count_line for l in wrapped) * lh + 14) if v else 0
    row_h = max(h_count * (size + 8) + 12, 52)
    axis_h = 0 if v else size + 14 + (size + 10 if s["label"] else 0)
    c.h = g["height"] if g.get("height") is not None else (320 + head_h + cat_h - 40 if v else head_h + n * row_h + axis_h + 12)
    plot_t = (g["y"] + head_h + math.ceil(size / 2) + 4) if v else (g["y"] + head_h + 6)
    plot_b = (g["y"] + c.h - cat_h - 6) if v else (g["y"] + c.h - axis_h - 6)
    if (plot_b - plot_t if v else (plot_b - plot_t) / n) < (120 if v else 30):
        fail(who, "the figure is too short; raise height" if v else f"the figure is too short for {n} groups; raise height")

    def y_of(u: float) -> float:
        return plot_b - (u - sc["min"]) / (sc["max"] - sc["min"]) * (plot_b - plot_t)

    def x_of(u: float) -> float:
        return plot_l + (u - sc["min"]) / (sc["max"] - sc["min"]) * (plot_r - plot_l)

    def px(u: float) -> float:
        return y_of(u) if v else x_of(u)

    def P(k: float, u: float) -> dict:
        return {"x": k, "y": y_of(u)} if v else {"x": x_of(u), "y": k}

    cat_a = plot_l if v else plot_t
    slot = (plot_r - plot_l if v else plot_b - plot_t) / n
    gap = 4
    bw = min(24 if all(k == "point" for k in s["kinds"]) else (64 if v else 40), (slot * 0.8 - (h_count - 1) * gap) / h_count)
    if bw < 8:
        fail(who, f"the groups are too narrow ({math.floor(bw)}px): raise width, use fewer groups / hues, or dir: 'h'")

    def kc(gi: int, hi: int) -> float:
        return cat_a + (gi + 0.5) * slot + (hi - (h_count - 1) / 2) * (bw + gap)

    ops = shade_ops(h_count)

    def fill_op(hi: int, kind: str) -> float:
        return (0.5 if kind == "bar" else 0.25) if h_count == 1 else ops[hi]

    def grp(gi: int) -> dict:
        return s["groups"][gi]

    def of(gi: int) -> str:
        return grp(gi).get("id") or f"#{gi}"

    def rect_ku(k0: float, k1: float, u0: float, u1: float, o: dict) -> int:
        a, b = P(k0, u0), P(k1, u1)
        return c.rect(_r1(min(a["x"], b["x"])), _r1(min(a["y"], b["y"])), _r1(abs(b["x"] - a["x"])), _r1(abs(b["y"] - a["y"])), o)

    def line_ku(k0: float, u0: float, k1: float, u1: float, o: dict) -> None:
        a, b = P(k0, u0), P(k1, u1)
        c.line(a["x"], a["y"], b["x"], b["y"], o)

    # legend, axis name
    glyphs = not rect_kind
    for l in legend:
        cy = g["y"] + l["row"] * (size + 12) + max(9, math.ceil(size * 0.64))
        if glyphs:
            c.path(marker_path(SHAPES[l["i"]] if l["i"] < len(SHAPES) else "disc", l["x"] + 7, cy, 6), {"fill": "accent", "op": 0.8})
        else:
            c.rect(l["x"], cy - 7, 14, 14, {"fill": "accent", "op": fill_op(l["i"], s["kinds"][0]), "stroke": "accent", "sw": 2})
        c.text(s["hues"][l["i"]], l["x"] + 20, c.mid(cy), "start", "text")
    axis_name = s["label"]
    if v and axis_name:
        c.text(axis_name, plot_l - 4, g["y"] + legend_h + size + 2, "start", "muted", {"bold": True})

    for t in sc["ticks"]:
        if v:
            c.line(plot_l - 6, y_of(t), plot_r, y_of(t), {"stroke": "text" if (t == 0 and "bar" in s["kinds"]) else "border"})
            c.text(tick(t), plot_l - 10, c.mid(y_of(t)), "end", "muted")
        else:
            c.line(x_of(t), plot_t, x_of(t), plot_b + 6, {"stroke": "text" if (t == 0 and "bar" in s["kinds"]) else "border"})
            c.text(tick(t), x_of(t), plot_b + size + 10, "middle", "muted")
    c.line(plot_l, plot_t, plot_l, plot_b, {"stroke": "border"})
    if not v and axis_name:
        c.text(axis_name, (plot_l + plot_r) / 2, plot_b + 2 * size + 22, "middle", "muted", {"bold": True})

    # category labels
    for gi, gr in enumerate(s["groups"]):
        cen = cat_a + (gi + 0.5) * slot
        own = of(gi)
        lines = list(wrapped[gi])
        total = len(lines) + count_line
        text = _count_text(gr)
        if v:
            c.lines(lines, cen, plot_b + size + 11, "middle", "text", {"bold": True, "of": own})
            if s["counts"]:
                c.text(text, cen, plot_b + size + 11 + len(lines) * lh, "middle", "muted", {"of": own})
        else:
            top = cen - (total - 1) * lh / 2 + size * 0.36
            c.lines(lines, plot_l - 10, top, "end", "text", {"bold": True, "of": own})
            if s["counts"]:
                c.text(text, plot_l - 10, top + len(lines) * lh, "end", "muted", {"of": own})
        if gr.get("id"):
            c.anchors.append(
                {"id": gr["id"], "x": _r1(cat_a + gi * slot), "y": _r1(plot_t), "w": _r1(slot), "h": _r1(plot_b - plot_t)}
                if v else
                {"id": gr["id"], "x": _r1(plot_l), "y": _r1(cat_a + gi * slot), "w": _r1(plot_r - plot_l), "h": _r1(slot)}
            )

    # the layers, in the order given
    def draw(fn) -> None:
        for gi, gr in enumerate(s["groups"]):
            for hi, x in enumerate(gr["series"]):
                if x is not None:
                    fn(x, gi, hi, kc(gi, hi))

    pts = "strip" in s["kinds"] or "swarm" in s["kinds"]
    marks: list[dict] = []

    def dot(shape: str, p: dict, r: float, o: dict) -> None:
        c.path(marker_path(shape, p["x"], p["y"], r), o)
        marks.append(p)

    def err_bar(x: dict, k: float, hi: int, own: str) -> None:
        if not x.get("err"):
            return
        cap = min(bw / 4, 8)
        line_ku(k, x["err"][0], k, x["err"][1], {"stroke": "text", "sw": 2, "of": own})
        for u in x["err"]:
            line_ku(k - cap, u, k + cap, u, {"stroke": "text", "sw": 2, "of": own})

    for kind in s["kinds"]:
        if kind == "bar":
            def _bar(x: dict, gi: int, hi: int, k: float) -> None:
                own = of(gi)
                name_part = f" / \"{x['name']}\"" if x["name"] else ""
                rect_ku(k - bw / 2, k + bw / 2, 0, x["mean"], {"fill": "accent", "op": fill_op(hi, "bar"), "stroke": "accent", "sw": 2, "solid": f"the bar of \"{grp(gi)['label']}\"{name_part}", "of": own})
                err_bar(x, k, hi, own)
            draw(_bar)
        if kind == "violin":
            dens: list[list[dict | None]] = []
            for gr in s["groups"]:
                row_d: list[dict | None] = []
                for x in gr["series"]:
                    if x is None:
                        row_d.append(None)
                        continue
                    b = x["box"]
                    grid = [b.min + (b.max - b.min) * i / 40 for i in range(41)]
                    kde_r = kde(x["values"], grid)
                    row_d.append({"grid": grid, **kde_r})
                dens.append(row_d)
            top_d = max((max(d["density"]) if d else 0) for row_d in dens for d in row_d)

            def _violin(x: dict, gi: int, hi: int, k: float) -> None:
                d = dens[gi][hi]
                own = of(gi)
                norm = top_d if s["scale"] == "area" else max(d["density"])
                half = [q / norm * bw / 2 for q in d["density"]]

                def side(sgn: int) -> list[dict]:
                    return [P(k + sgn * half[i], u) for i, u in enumerate(d["grid"])]

                pts_all = side(-1) + list(reversed(side(1)))
                pth = " ".join(f"{'L' if i else 'M'}{js_num(_r1(p['x']))},{js_num(_r1(p['y']))}" for i, p in enumerate(pts_all)) + " Z"
                c.path(pth, {"fill": "accent", "op": fill_op(hi, "violin"), "stroke": "accent", "sw": 2, "of": own})
                a, b = P(k - bw / 2, x["box"].min), P(k + bw / 2, x["box"].max)
                name_part = f" / \"{x['name']}\"" if x["name"] else ""
                c.solids.append({"x": _r1(min(a["x"], b["x"])), "y": _r1(min(a["y"], b["y"])), "w": _r1(abs(b["x"] - a["x"])), "h": _r1(abs(b["y"] - a["y"])), "label": f"the violin of \"{grp(gi)['label']}\"{name_part}"})
                line_ku(k, x["box"].q1, k, x["box"].q3, {"stroke": "text", "sw": 5, "of": own})
                m = P(k, x["box"].median)
                c.path(marker_path("disc", m["x"], m["y"], 2.5), {"fill": "bg", "of": own})
            draw(_violin)
        if kind == "box":
            def _box(x: dict, gi: int, hi: int, k: float) -> None:
                own = of(gi)
                b = x["box"]
                cap = bw / 4
                line_ku(k, b.lo, k, b.q1, {"stroke": "accent", "sw": 2, "of": own})
                line_ku(k, b.q3, k, b.hi, {"stroke": "accent", "sw": 2, "of": own})
                for u in (b.lo, b.hi):
                    line_ku(k - cap, u, k + cap, u, {"stroke": "accent", "sw": 2, "of": own})
                name_part = f" / \"{x['name']}\"" if x["name"] else ""
                rect_ku(k - bw / 2, k + bw / 2, b.q1, b.q3, {"fill": "accent", "op": fill_op(hi, "box"), "stroke": "accent", "sw": 2, "solid": f"the box of \"{grp(gi)['label']}\"{name_part}", "of": own})
                line_ku(k - bw / 2, b.median, k + bw / 2, b.median, {"stroke": "text", "sw": 3, "of": own})
                if not pts:
                    for u in b.fliers:
                        dot("ring", P(k, u), 3, {"fill": "none", "stroke": "accent", "sw": 2, "of": own})
            draw(_box)
        if kind == "point":
            dash_opts = ["", "6,4", "2,4", "10,4,2,4"]
            for hi in range(h_count):
                through = []
                for gi, gr in enumerate(s["groups"]):
                    x = gr["series"][hi] if hi < len(gr["series"]) else None
                    if x is not None:
                        through.append(P(kc(gi, hi), x["mean"]))
                if len(through) > 1:
                    dash = dash_opts[hi] if hi < len(dash_opts) and dash_opts[hi] else None
                    path_d = " ".join(f"{'L' if i else 'M'}{js_num(_r1(p['x']))},{js_num(_r1(p['y']))}" for i, p in enumerate(through))
                    c.path(path_d, {"fill": "none", "stroke": "accent", "sw": 2, "dash": dash, "of": [of(gi) for gi in range(len(s["groups"]))]})

            def _point(x: dict, gi: int, hi: int, k: float) -> None:
                own = of(gi)
                err_bar(x, k, hi, own)
                dot(SHAPES[hi] if hi < len(SHAPES) else "disc", P(k, x["mean"]), 5.5, {"fill": "accent", "stroke": "bg", "sw": 1.5, "of": own})
            draw(_point)
        if kind in ("strip", "swarm"):
            def _strip(x: dict, gi: int, hi: int, k: float) -> None:
                own = of(gi)
                r, free = 3.5, bw / 2 - 3.5
                if kind == "swarm":
                    offs = swarm_offsets([px(u) for u in x["values"]], 2 * r + 1, free)
                else:
                    offs = [((i * 0.6180339887) % 1 - 0.5) * 2 * free for i in range(len(x["values"]))]
                if offs is None:
                    name_part = f" / \"{x['name']}\"" if x["name"] else ""
                    fail(who, f"the points of \"{grp(gi)['label']}\"{name_part} do not fit side by side in {math.floor(bw)}px (raise width / height, use fewer groups, or stripplot)")
                    return
                for i, u in enumerate(x["values"]):
                    dot(SHAPES[hi] if hi < len(SHAPES) else "disc", P(k + offs[i], u), r, {"fill": "accent", "op": 0.8, "stroke": "bg", "sw": 1, "of": own})
            draw(_strip)
    for m in marks:
        c.marks.append({"x": m["x"] - 4, "y": m["y"] - 4, "w": 8, "h": 8})

    if s["values"] != "none":
        def _label(x: dict, gi: int, hi: int, k: float) -> None:
            own = of(gi)
            u = _value_at(s, x)
            text = f"{num_text(u)}{s['unit']}"
            p = P(k, u)
            half = bw / 2 + 6
            hi_top = max(x["err"]) if x.get("err") else x["box"].hi
            top = P(k, hi_top)
            if v:
                cands = [
                    {"x": p["x"] + half, "y": c.mid(p["y"]), "anchor": "start"},
                    {"x": p["x"] - half, "y": c.mid(p["y"]), "anchor": "end"},
                    {"x": top["x"], "y": top["y"] - 8, "anchor": "middle"},
                ]
            else:
                cands = [
                    {"x": top["x"] + 8, "y": c.mid(top["y"]), "anchor": "start"},
                    {"x": p["x"], "y": p["y"] - bw / 2 - 5, "anchor": "middle"},
                    {"x": p["x"], "y": p["y"] + bw / 2 + size + 3, "anchor": "middle"},
                ]
            above = "bar" in s["kinds"] or "point" in s["kinds"]
            order = [cands[2], cands[0], cands[1]] if above else cands
            if not c.place(text, order, "text", {"bold": True, "of": own}):
                name_part = f" {x['name']}" if x["name"] else ""
                c.omitted.append(f"{grp(gi)['label']}{name_part} {text}")
        draw(_label)

    return c.done()


def cat_band(who: str, data, opts: dict | None = None, kind: str | None = None) -> ChartBand:
    """lib/charts-dsl.ts's catBand() + the catplot()/boxplot()/.../barplot() DSL wrappers."""
    opts = opts or {}
    spec = resolve_cat(who, data, opts, kind if kind is not None else "box")
    alt = opts.get("alt") if opts.get("alt") is not None else cat_alt(spec)
    return ChartBand(kind="catplot", spec=spec, alt=alt, **common_chart_opts(who, id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
