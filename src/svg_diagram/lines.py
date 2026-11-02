"""1:1 port of lib/charts-lines.ts's linesOpts()/burndownOpts()/burnupOpts()/
strategyCanvasOpts() — the ergonomic layer that turns a multi-series line chart (or a
burndown/burnup/strategy-canvas preset) into the PlaneOpts a plane() understands. The
actual layout/render is plane.layout_plane()/render_plane() — this module only builds the
options dict (and, for convenience, combines that with plane_band() into one call).

Golden master: lib/charts-lines.ts + lib/dsl/charts.ts's lines()/strategyCanvas()/
burndown()/burnup() (Node.js, svg-diagram).
"""

from __future__ import annotations

from .charts_base import check_text, fail, finite_num, nice_scale, num_text
from .emit_common import js_round
from .plane import plane_band
from .tokens import ROLES

STYLE: list[dict] = [
    {"tone": "accent", "dashed": False, "shape": "disc"},
    {"tone": "text", "dashed": True, "shape": "square"},
    {"tone": "danger", "dashed": False, "shape": "diamond"},
    {"tone": "muted", "dashed": True, "shape": "triangle"},
    {"tone": "accent", "dashed": True, "shape": "hole"},
    {"tone": "text", "dashed": False, "shape": "cross"},
]


def lines_opts(series: list[dict], opts: dict | None = None) -> dict:
    """lib/charts-lines.ts:53-143 linesOpts()."""
    opts = opts or {}
    who = "lines"
    if not isinstance(series, list) or len(series) == 0:
        fail(who, "needs at least one series")
    non_ideal = [s for s in series if not s.get("ideal")]
    if len(non_ideal) > 6:
        fail(who, f"{len(non_ideal)} series are too many to tell apart (at most 6, besides ideal lines)")
    cats = (opts.get("x") or {}).get("categories")
    if cats is not None and (not isinstance(cats, list) or len(cats) < 2):
        fail(who, "x.categories needs at least two names")
    if cats:
        for i, c in enumerate(cats):
            check_text(who, f"category {i + 1}", c)
    labels = [check_text(who, f"series {i + 1}'s label", s["label"]) for i, s in enumerate(series)]
    if len(set(labels)) != len(labels):
        fail(who, "each series needs its own label")

    pts: list[list] = []
    for s in series:
        if not isinstance(s.get("values"), list) or len(s["values"]) == 0:
            fail(who, f'series "{s["label"]}" has no values')
        row: list = []
        for i, v in enumerate(s["values"]):
            if v is None:
                if not cats:
                    fail(who, f'series "{s["label"]}": null (a gap) needs x.categories')
                row.append(None)
                continue
            if isinstance(v, list):
                if cats:
                    fail(who, f'series "{s["label"]}": [x, y] pairs belong to a numeric x axis; with x.categories give one value per category')
                row.append([finite_num(who, f'"{s["label"]}" x', v[0]), finite_num(who, f'"{s["label"]}" y', v[1])])
                continue
            if not cats:
                fail(who, f'series "{s["label"]}": give [x, y] pairs, or x.categories to give one value per category')
            row.append([i, finite_num(who, f'"{s["label"]}" value {i + 1}', v)])
        pts.append(row)
    if cats:
        for k, p in enumerate(pts):
            if len(p) != len(cats):
                fail(who, f'series "{series[k]["label"]}" has {len(p)} values for {len(cats)} categories (use null for a gap)')
    else:
        for k, p in enumerate(pts):
            xs = [q[0] for q in p]
            if any(i > 0 and xs[i] <= xs[i - 1] for i in range(len(xs))):
                fail(who, f'series "{series[k]["label"]}": x must increase along the series')
    real = [q for row in pts for q in row if q is not None]
    if not real:
        fail(who, "every value is null")

    xs_all = [q[0] for q in real]
    ys_all = [q[1] for q in real] + ([opts["target"]["at"]] if opts.get("target") else [])
    if cats:
        x: dict = {"min": -0.5, "max": len(cats) - 0.5, "ticks": [{"at": i, "label": c} for i, c in enumerate(cats)]}
        if (opts.get("x") or {}).get("label") is not None:
            x["label"] = opts["x"]["label"]
    else:
        xo = opts.get("x") or {}
        sc = nice_scale(xo.get("min") if xo.get("min") is not None else min(xs_all), xo.get("max") if xo.get("max") is not None else max(xs_all), 6)
        x = {"min": xo.get("min") if xo.get("min") is not None else sc["min"], "max": xo.get("max") if xo.get("max") is not None else sc["max"]}
        if xo.get("step") is not None:
            x["step"] = xo["step"]
        elif xo.get("ticks") is None:
            x["step"] = sc["step"]
        if xo.get("ticks") is not None:
            x["ticks"] = xo["ticks"]
        if xo.get("label") is not None:
            x["label"] = xo["label"]
    yo = opts.get("y") or {}
    ysc = nice_scale(yo.get("min") if yo.get("min") is not None else min([0, *ys_all]), yo.get("max") if yo.get("max") is not None else max(ys_all), 5)
    y: dict = {"min": yo.get("min") if yo.get("min") is not None else ysc["min"], "max": yo.get("max") if yo.get("max") is not None else ysc["max"]}
    if yo.get("step") is not None:
        y["step"] = yo["step"]
    elif yo.get("ticks") is None:
        y["step"] = ysc["step"]
    if yo.get("ticks") is not None:
        y["ticks"] = yo["ticks"]
    if yo.get("label") is not None:
        y["label"] = yo["label"]
    for q in real:
        if q[1] < (y.get("min") or 0) or q[1] > y["max"]:
            fail(who, f"a value ({num_text(q[1])}) is outside the y axis {y.get('min') or 0}-{y['max']}")
        if q[0] < (x.get("min") or 0) or q[0] > x["max"]:
            fail(who, f"an x ({num_text(q[0])}) is outside the x axis {x.get('min') or 0}-{x['max']}")

    points: list[dict] = []
    paths: list[dict] = []
    named = opts.get("endLabels") is not False
    mark = opts.get("markers") is not False
    for k, s in enumerate(series):
        prior_non_ideal = len([o for o in series[:k] if not o.get("ideal")])
        st = STYLE[prior_non_ideal]
        tone = "muted" if s.get("ideal") else st["tone"]
        dashed = True if s.get("ideal") else st["dashed"]
        runs: list[list] = []
        run: list = []
        for q in pts[k]:
            if q is not None:
                run.append(q)
            else:
                if run:
                    runs.append(run)
                run = []
        if run:
            runs.append(run)
        for r in runs:
            if len(r) >= 2:
                path_item: dict = {"through": r, "tone": tone, "dashed": dashed}
                if s.get("smooth"):
                    path_item["smooth"] = True
                paths.append(path_item)
        last_run = runs[-1]
        end = last_run[-1]
        for r in runs:
            for q in r:
                is_end = q is end
                if s.get("ideal") and not is_end:
                    continue
                if not mark and not is_end:
                    continue
                point_item: dict = {"at": q, "tone": tone, "shape": "ring" if s.get("ideal") else st["shape"]}
                if is_end and named and not s.get("ideal"):
                    point_item["label"] = s["label"]
                    point_item["labelAt"] = "auto" if (cats and q[0] != len(cats) - 1) else "right"
                    if cats and q[0] != len(cats) - 1:
                        point_item["labelLeader"] = True
                points.append(point_item)

    mid_labels: list[dict] = []
    if named:
        for k, s in enumerate(series):
            if not s.get("ideal"):
                continue
            q = [v for v in pts[k] if v is not None]
            a, b = q[0], q[-1]
            offset = [10, 24] if b[1] >= a[1] else [10, -12]
            mid_labels.append({"at": [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], "text": s["label"], "anchor": "start", "tone": "muted", "bold": True, "offset": offset})

    def find(name: str, index: int) -> list:
        k = labels.index(name) if name in labels else -1
        if k < 0:
            fail(who, f"annotate: no series \"{name}\" (series: {', '.join(labels)})")
        q = pts[k][index] if 0 <= index < len(pts[k]) else None
        if q is None:
            fail(who, f'annotate: series "{name}" has no point {index}')
        return q

    for a in opts.get("annotate") or []:
        check_text(who, "an annotation label", a["label"])
        at = a["at"] if isinstance(a["at"], list) else find(a["at"]["series"], a["at"]["index"])
        points.append({"at": at, "tone": a.get("tone") or "danger", "shape": "ring", "label": a["label"], "labelAt": a.get("labelAt") or "above"})

    lines: list[dict] = []
    extra: list[dict] = list(mid_labels)
    if opts.get("target"):
        finite_num(who, "target.at", opts["target"]["at"])
        lines.append({"from": [x.get("min") or 0, opts["target"]["at"]], "to": [x["max"], opts["target"]["at"]], "tone": "danger", "dashed": True})
        size = ROLES[opts.get("labelRole") or "note"]
        lift = js_round(size * 5 / 14) + 9
        if opts["target"].get("label"):
            extra.append({"at": [x["max"], opts["target"]["at"]], "text": opts["target"]["label"], "anchor": "end", "tone": "danger", "bold": True, "offset": [-6, -lift]})

    result: dict = {"x": x, "y": y, "points": points, "paths": paths}
    if lines:
        result["lines"] = lines
    if extra:
        result["labels"] = extra
    result["grid"] = opts.get("grid") is not False
    result["height"] = opts.get("height") if opts.get("height") is not None else 340
    result["endLabels"] = named
    if opts.get("id") is not None:
        result["id"] = opts["id"]
    if opts.get("width") is not None:
        result["width"] = opts["width"]
    if opts.get("labelRole") is not None:
        result["labelRole"] = opts["labelRole"]
    if opts.get("reveal") is not None:
        result["reveal"] = opts["reveal"]
    if opts.get("until") is not None:
        result["until"] = opts["until"]
    return result


def strategy_canvas_opts(factors: list[str], series: list[dict], opts: dict | None = None) -> tuple[list[dict], dict]:
    """lib/charts-lines.ts:154-158 strategyCanvasOpts()."""
    opts = opts or {}
    lv = opts.get("levels") or {}
    min_v = lv.get("min") if lv.get("min") is not None else 0
    max_v = lv.get("max") if lv.get("max") is not None else 5
    rest = {k: v for k, v in opts.items() if k != "levels"}
    line_series = [{"label": s["label"], "values": s["values"]} for s in series]
    x_opts = {"categories": factors, **(opts.get("x") or {})}
    y_opts = {"min": min_v, "max": max_v, "ticks": [{"at": min_v, "label": lv.get("low") or "低い"}, {"at": max_v, "label": lv.get("high") or "高い"}], "label": "提供価値の水準", **(opts.get("y") or {})}
    return line_series, {**rest, "x": x_opts, "y": y_opts}


def burndown_opts(spec: dict, opts: dict | None = None) -> tuple[list[dict], dict]:
    """lib/charts-lines.ts:168-175 burndownOpts()."""
    opts = opts or {}
    if not (spec["days"] >= 1) or not isinstance(spec["days"], int):
        fail("burndown", f"days must be a whole number >= 1 (got {spec['days']})")
    finite_num("burndown", "total", spec["total"], min=0)
    if len(spec["actual"]) > spec["days"] + 1:
        fail("burndown", f"actual has {len(spec['actual'])} values for days 0-{spec['days']}")
    actual = []
    for i, v in enumerate(spec["actual"]):
        if v is not None:
            actual.append([i, finite_num("burndown", f"actual[{i}]", v, min=0)])
    series = [{"label": "理想", "values": [[0, spec["total"]], [spec["days"], 0]], "ideal": True}, {"label": "実績", "values": actual}]
    x_opts = {"min": 0, "max": spec["days"], "label": "日", **({} if spec["days"] > 14 else {"step": 1}), **(opts.get("x") or {})}
    y_max = (opts.get("y") or {}).get("max")
    if y_max is None:
        y_max = nice_scale(0, max([spec["total"], *(q[1] for q in actual)]), 5)["max"]
    y_opts = {"min": 0, "max": y_max, "label": "残り", **(opts.get("y") or {})}
    return series, {**opts, "x": x_opts, "y": y_opts}


def burnup_opts(spec: dict, opts: dict | None = None) -> tuple[list[dict], dict]:
    """lib/charts-lines.ts:184-191 burnupOpts()."""
    opts = opts or {}
    if not (spec["days"] >= 1) or not isinstance(spec["days"], int):
        fail("burnup", f"days must be a whole number >= 1 (got {spec['days']})")
    if isinstance(spec["scope"], (int, float)):
        scope = [[0, spec["scope"]], [spec["days"], spec["scope"]]]
    else:
        scope = [[i, finite_num("burnup", f"scope[{i}]", v, min=0)] for i, v in enumerate(spec["scope"])]
    if len(scope) < 2:
        fail("burnup", "scope needs a value for each day (at least days 0 and 1), or one number")
    done = []
    for i, v in enumerate(spec["done"]):
        if v is not None:
            done.append([i, finite_num("burnup", f"done[{i}]", v, min=0)])
    top = max([q[1] for q in scope] + [q[1] for q in done])
    series = [{"label": "スコープ", "values": scope, "ideal": True}, {"label": "完了", "values": done}]
    x_opts = {"min": 0, "max": spec["days"], "label": "日", **({} if spec["days"] > 14 else {"step": 1}), **(opts.get("x") or {})}
    y_max = (opts.get("y") or {}).get("max")
    if y_max is None:
        y_max = nice_scale(0, top, 5)["max"]
    y_opts = {"min": 0, "max": y_max, "label": "完了", **(opts.get("y") or {})}
    return series, {**opts, "x": x_opts, "y": y_opts}


def lines_band(series: list[dict], opts: dict | None = None) -> dict:
    """lib/dsl/charts.ts's lines(): plane(linesOpts(series, opts))."""
    return plane_band(lines_opts(series, opts))


def strategy_canvas_band(factors: list[str], series: list[dict], opts: dict | None = None) -> dict:
    """lib/dsl/charts.ts's strategyCanvas(): lines(...strategyCanvasOpts(factors, series, opts))."""
    line_series, lo = strategy_canvas_opts(factors, series, opts)
    return lines_band(line_series, lo)


def burndown_band(spec: dict, opts: dict | None = None) -> dict:
    """lib/dsl/charts.ts's burndown(): lines(...burndownOpts(spec, opts))."""
    series, lo = burndown_opts(spec, opts)
    return lines_band(series, lo)


def burnup_band(spec: dict, opts: dict | None = None) -> dict:
    """lib/dsl/charts.ts's burnup(): lines(...burnupOpts(spec, opts))."""
    series, lo = burnup_opts(spec, opts)
    return lines_band(series, lo)
