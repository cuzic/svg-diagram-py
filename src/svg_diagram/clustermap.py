"""1:1 port of lib/charts-cluster.ts's layoutCluster() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and lib/charts-dsl.ts's clusterBand() — seaborn's
clustermap, built on lib/stats.ts's averageLinkage()/dendrogramOrder().

clusterTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
the other chart kinds' *Texts() helpers.

Golden master: lib/charts-cluster.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .charts_base import Canvas, ChartBand, check_ids, check_text, common_chart_opts, fail, finite_num, ink_on_shade, num_text
from .emit_common import js_num, round1
from .stats import average_linkage, dendrogram_order

_MAX = 40


def _transpose(m: list[list[float]]) -> list[list[float]]:
    return [[row[j] for row in m] for j in range(len(m[0]))]


def _minmax(v: list[float]) -> list[float]:
    lo, hi = min(v), max(v)
    return [(q - lo) / (hi - lo) if hi > lo else 0.5 for q in v]


def resolve_cluster(rows: list[str], cols: list[str], values: list[list[float]], opts: dict | None) -> dict:
    """lib/charts-cluster.ts:30-44 resolveCluster()."""
    opts = opts or {}
    check_ids("clustermap", [], opts.get("id"))
    if not isinstance(rows, list) or len(rows) < 2:
        fail("clustermap", "needs at least two rows")
    if not isinstance(cols, list) or len(cols) < 2:
        fail("clustermap", "needs at least two columns")
    if len(rows) > _MAX or len(cols) > _MAX:
        fail("clustermap", f"at most {_MAX} rows and {_MAX} columns (got {len(rows)} × {len(cols)})")
    if not isinstance(values, list) or len(values) != len(rows) or any(not isinstance(r, list) or len(r) != len(cols) for r in values):
        fail("clustermap", f"values must be {len(rows)} rows of {len(cols)} numbers")
    scale = opts.get("scale")
    if scale is not None and scale not in ("row", "col"):
        fail("clustermap", f"scale must be 'row' or 'col' (got {scale!r})")
    for i, r in enumerate(rows):
        check_text("clustermap", f"row {i + 1}'s name", r)
    for i, cl in enumerate(cols):
        check_text("clustermap", f"column {i + 1}'s name", cl)
    v = [[finite_num("clustermap", f"value ({rows[i]}, {cols[j]})", q) for j, q in enumerate(row)] for i, row in enumerate(values)]
    all_v = [q for row in v for q in row]
    lo, hi = min(all_v), max(all_v)
    if scale == "row":
        shade = [_minmax(row) for row in v]
    elif scale == "col":
        shade = _transpose([_minmax(col) for col in _transpose(v)])
    else:
        shade = [[(q - lo) / (hi - lo) if hi > lo else 0.5 for q in row] for row in v]

    def tree(data: list[list[float]]) -> dict:
        merges = average_linkage(data)
        order_pos = dendrogram_order(merges, len(data))
        return {"merges": merges, **order_pos}

    row_tree = None if opts.get("rows") is False else tree(shade)
    col_tree = None if opts.get("cols") is False else tree(_transpose(shade))
    spec: dict = {"rows": list(rows), "cols": list(cols), "values": v, "unit": opts.get("unit") or "", "showValues": opts.get("values") if opts.get("values") is not None else True, "shade": shade}
    if scale:
        spec["scale"] = scale
    if row_tree:
        spec["rowTree"] = row_tree
    if col_tree:
        spec["colTree"] = col_tree
    return spec


def cluster_alt(s: dict) -> str:
    """lib/charts-cluster.ts:45-48 clusterAlt()."""
    ro = s["rowTree"]["order"] if s.get("rowTree") else list(range(len(s["rows"])))
    co = s["colTree"]["order"] if s.get("colTree") else list(range(len(s["cols"])))
    all_v = [q for row in s["values"] for q in row]
    row_names = "・".join(s["rows"][i] for i in ro)
    col_names = "・".join(s["cols"][i] for i in co)
    return f"クラスタ付きヒートマップ（行 {row_names} / 列 {col_names}、値 {num_text(min(all_v))}〜{num_text(max(all_v))}{s['unit']}）"


_r1 = round1


def layout_cluster(s: dict, g: dict) -> dict:
    """lib/charts-cluster.ts:56-102 layoutCluster()."""
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    lh = c.line_h()
    nr, nc = len(s["rows"]), len(s["cols"])
    ro = s["rowTree"]["order"] if s.get("rowTree") else list(range(nr))
    co = s["colTree"]["order"] if s.get("colTree") else list(range(nc))
    row_w = min(max(c.tw(t) for t in s["rows"]) + 12, g["w"] * 0.22)
    dw = 80 if s.get("rowTree") else 0
    dh = 64 if s.get("colTree") else 0
    left, right = g["x"] + dw + 6, g["x"] + g["w"] - row_w - 4
    cw = (right - left) / nc
    if cw < 14:
        fail("clustermap", "the figure is too narrow for its columns (raise width, or use fewer columns)")
    col_lines = [c.wrap(t, cw - 4) for t in s["cols"]]
    lab_h = max(len(l) for l in col_lines) * lh + 10
    rh = max(size + 6, 22)
    top = g["y"] + dh + 6
    c.h = g["height"] if g.get("height") is not None else dh + 6 + nr * rh + lab_h + size + 30
    cell_h = (c.h - dh - 6 - lab_h - size - 30) / nr if g.get("height") is not None else rh
    if cell_h < size + 2:
        fail("clustermap", "the figure is too short for its rows (raise height, or use fewer rows)")
    all_v = [q for row in s["values"] for q in row]
    lo, hi = min(all_v), max(all_v)

    for y, ri in enumerate(ro):
        for x, ci in enumerate(co):
            t = s["shade"][ri][ci]
            op = _r1(0.1 + 0.8 * t)
            ink = ink_on_shade(op)
            text = f"{num_text(s['values'][ri][ci])}{s['unit']}"
            host = c.rect(_r1(left + x * cw), _r1(top + y * cell_h), _r1(cw), _r1(cell_h), {"fill": "accent", "op": op, "stroke": "bg", "sw": 1, "solid": f"the cell ({s['rows'][ri]}, {s['cols'][ci]})"})
            if s["showValues"] and c.tw(text, True) + 6 <= cw and size + 2 <= cell_h:
                c.text(text, left + (x + 0.5) * cw, c.mid(top + (y + 0.5) * cell_h), "middle", ink, {"bold": True, "host": host, "on": {"fill": "accent", "op": op, "ink": ink}})
    for y, ri in enumerate(ro):
        c.text(s["rows"][ri], right + 8, c.mid(top + (y + 0.5) * cell_h), "start", "text")
    grid_b = top + nr * cell_h
    for x, ci in enumerate(co):
        c.lines(col_lines[ci], left + (x + 0.5) * cw, grid_b + size + 6, "middle", "text")

    def tree(t: dict, n: int, along, away) -> list[str]:
        max_h = max((m.height for m in t["merges"]), default=0) or 1

        def h_of(node_id: int) -> float:
            return 0 if node_id < n else t["merges"][node_id - n].height / max_h

        def xy(v: float) -> str:
            return js_num(_r1(v))

        seg: list[str] = []
        for k, m in enumerate(t["merges"]):
            h = h_of(n + k)
            for ch in (m.a, m.b):
                seg.append(f"M{xy(along(t['pos'][ch]))},{xy(away(h_of(ch)))} L{xy(along(t['pos'][ch]))},{xy(away(h))}")
            seg.append(f"M{xy(along(t['pos'][m.a]))},{xy(away(h))} L{xy(along(t['pos'][m.b]))},{xy(away(h))}")
        return seg

    if s.get("colTree"):
        segs = tree(s["colTree"], nc, lambda p: left + (p + 0.5) * cw, lambda h: g["y"] + dh - h * (dh - 4))
        c.path(" ".join(segs), {"fill": "none", "stroke": "text", "sw": 1.5})
    if s.get("rowTree"):
        segs = tree(s["rowTree"], nr, lambda p: top + (p + 0.5) * cell_h, lambda h: left - 6 - h * (dw - 8))
        c.path(" ".join(_swap_coords(seg) for seg in segs), {"fill": "none", "stroke": "text", "sw": 1.5})

    leg_y = grid_b + lab_h + 8
    min_text = f"最小 {num_text(lo)}{s['unit']}"
    sx0 = g["x"] + c.tw(min_text) + 8
    c.text(min_text, g["x"], c.mid(leg_y + 7), "start", "muted")
    for k in range(5):
        c.rect(sx0 + k * 18, leg_y, 18, 14, {"fill": "accent", "op": _r1(0.1 + 0.8 * k / 4), "stroke": "border", "sw": 1})
    c.text(f"最大 {num_text(hi)}{s['unit']}", sx0 + 5 * 18 + 8, c.mid(leg_y + 7), "start", "muted")
    c.h = max(c.h, leg_y + 14 + 6 - g["y"])
    return c.done()


def _swap_coords(seg: str) -> str:
    """lib/charts-cluster.ts:90's `.replace(/(-?[\\d.]+),(-?[\\d.]+)/g, '$2,$1')` — swap each
    x,y pair in a path's M/L commands (the row dendrogram is drawn with x/y transposed)."""
    import re

    return re.sub(r"(-?[\d.]+),(-?[\d.]+)", r"\2,\1", seg)


def cluster_band(rows: list[str], cols: list[str], values: list[list[float]], opts: dict | None = None) -> ChartBand:
    """lib/charts-dsl.ts's clusterBand() + the clustermap() DSL wrapper."""
    opts = opts or {}
    spec = resolve_cluster(rows, cols, values, opts)
    alt = opts.get("alt") if opts.get("alt") is not None else cluster_alt(spec)
    return ChartBand(kind="clustermap", spec=spec, alt=alt, **common_chart_opts("clustermap", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
