"""1:1 port of lib/charts-treemap.ts's layoutTreemap() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the treemap() DSL constructor (lib/charts-dsl.ts's
treemapBand()) — defaults + the structural validations that affect layout.

treemapTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
heatmapTexts()/sankeyTexts()/radarTexts().

Node `TreemapNode` objects are JS `Map` keys by reference identity (`weight.get(n)`); this
port uses Python's `id(node_dict)` the same way, which works because the spec tree is built
once (by resolve_treemap()) and the SAME dict instances are walked consistently by plan()
within one layout_treemap() call.

Golden master: lib/charts-treemap.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .charts_base import Canvas, ChartBand, check_ids, check_text, common_chart_opts, fail, finite_num, ink_on_shade, num_text
from .charts_base import _to_precision as to_precision
from .emit_common import js_round, round1


def _total_of(n: dict) -> float:
    """lib/charts-treemap.ts:27 totalOf()."""
    if n.get("children"):
        return sum(_total_of(c) for c in n["children"])
    return n.get("value") or 0


def resolve_treemap(tree, opts: dict) -> dict:
    """lib/charts-treemap.ts:28-50 resolveTreemap()."""
    nodes = list(tree) if isinstance(tree, list) else [tree]
    if not nodes or not nodes[0]:
        fail("treemap", "needs at least one node")
    ids: list = []

    def walk(n: dict, depth: int, where: str) -> dict:
        check_text("treemap", f"{where}'s label", n["label"])
        if depth > 4:
            fail("treemap", f'"{n["label"]}" is nested more than 4 levels deep')
        ids.append(n.get("id"))
        if n.get("children"):
            if n.get("value") is not None:
                t = _total_of(n)
                if abs(finite_num("treemap", f'"{n["label"]}" value', n["value"]) - t) > 1e-9 * max(1, t):
                    fail("treemap", f'"{n["label"]}" is {n["value"]} but its children add up to {num_text(to_precision(t, 12))} (leave its value out)')
            if n.get("tone") is not None:
                fail("treemap", f'"{n["label"]}": a group takes no tone (set it on a leaf)')
            result: dict = {"label": n["label"], "children": [walk(c, depth + 1, f'"{n["label"]}" child {i + 1}') for i, c in enumerate(n["children"])]}
            if n.get("id") is not None:
                result["id"] = n["id"]
            return result
        v = finite_num("treemap", f'"{n["label"]}" value', n.get("value"), min=0)
        if n.get("tone") is not None and n["tone"] not in ("accent", "danger"):
            fail("treemap", f'"{n["label"]}": tone must be accent or danger')
        result = {"label": n["label"], "value": v}
        if n.get("tone") is not None:
            result["tone"] = n["tone"]
        if n.get("id") is not None:
            result["id"] = n["id"]
        return result

    out = [walk(n, 1, f"node {i + 1}") for i, n in enumerate(nodes)]
    check_ids("treemap", ids, opts.get("id"))
    total = sum(_total_of(n) for n in out)
    if not (total > 0):
        fail("treemap", "every value is 0")
    return {"nodes": out, "unit": opts.get("unit") or "", "percent": bool(opts.get("percent")), "strict": bool(opts.get("strict")), "total": total}


def _share(v: float, total: float) -> str:
    return f"{num_text(js_round(v / total * 1000) / 10)}%"


def _value_text(v: float, s: dict) -> str:
    base = f"{num_text(to_precision(v, 12))}{s['unit']}"
    if s["percent"]:
        base += f" ({_share(v, s['total'])})"
    return base


def treemap_alt(s: dict) -> str:
    """lib/charts-treemap.ts:53-56 treemapAlt()."""

    def line(n: dict) -> str:
        if n.get("children"):
            return f"{n['label']}（計 {_value_text(_total_of(n), s)}）: {'、'.join(line(c) for c in n['children'])}"
        return f"{n['label']} {_value_text(n.get('value') or 0, s)}"

    return f"ツリーマップ（全体 {_value_text(s['total'], s)}）: {'、'.join(line(n) for n in s['nodes'])}"


def squarify(items: list[dict], x: float, y: float, w: float, h: float) -> list[dict]:
    """lib/charts-treemap.ts:69-91 squarify() (Bruls, Huizing, van Wijk)."""
    lst = sorted((i for i in items if i["v"] > 0), key=lambda i: -i["v"])
    total = sum(i["v"] for i in lst)
    out: list[dict] = []
    if not lst or not (w > 0) or not (h > 0):
        return out
    scale = w * h / total
    areas = [i["v"] * scale for i in lst]

    def worst(row: list[float], side: float) -> float:
        rs = sum(row)
        mx, mn = max(row), min(row)
        return max(side * side * mx / (rs * rs), rs * rs / (side * side * mn))

    i = 0
    rx, ry, rw, rh = x, y, w, h
    while i < len(lst):
        side = min(rw, rh)
        row = [areas[i]]
        j = i + 1
        while j < len(lst) and worst([*row, areas[j]], side) <= worst(row, side):
            row.append(areas[j])
            j += 1
        rs = sum(row)
        thick = rs / side
        off = 0.0
        for k in range(i, j):
            length = areas[k] / thick
            if rw >= rh:
                out.append({"n": lst[k]["n"], "v": lst[k]["v"], "x": rx, "y": ry + off, "w": thick, "h": length})
            else:
                out.append({"n": lst[k]["n"], "v": lst[k]["v"], "x": rx + off, "y": ry, "w": length, "h": thick})
            off += length
        if rw >= rh:
            rx += thick
            rw -= thick
        else:
            ry += thick
            rh -= thick
        i = j
    return out


def layout_treemap(s: dict, g: dict) -> dict:
    """lib/charts-treemap.ts:99-193 layoutTreemap()."""
    size = g["size"]
    h = g["height"] if g.get("height") is not None else js_round(min(480, max(300, g["w"] * 0.5)))
    c = Canvas(g["x"], g["y"], g["w"], h, size, g["widthOf"], g["wrap"])
    lh = c.line_h()

    r1 = round1

    head_h = size + 10

    def plan(weight: dict) -> list[dict]:
        out: list[dict] = []

        def w_of(n: dict) -> float:
            if n.get("children"):
                return sum(w_of(k) for k in n["children"])
            return weight.get(id(n), 0)

        def lay(n: dict, cell: dict, gi: int) -> None:
            if not n.get("children"):
                x, y = r1(cell["x"] + 1), r1(cell["y"] + 1)
                w, hh = r1(cell["w"] - 2), r1(cell["h"] - 2)
                out.append({"k": "gone", "n": n} if w <= 0 or hh <= 0 else {"k": "leaf", "n": n, "gi": gi, "x": x, "y": y, "w": w, "h": hh})
                return
            x, y = cell["x"] + 2, cell["y"] + 2
            w, hh = cell["w"] - 4, cell["h"] - 4
            if w <= 0 or hh <= 0:
                out.append({"k": "gone", "n": n})
                return
            text = f"{n['label']} {_value_text(_total_of(n), s)}"
            if hh > head_h + 24 and c.tw(text, True) <= w - 10:
                head = "full"
            elif hh > head_h + 24 and c.tw(n["label"], True) <= w - 10:
                head = "name"
            else:
                head = "none"
            out.append({"k": "group", "n": n, "gi": gi, "x": x, "y": y, "w": w, "h": hh, "head": head})
            inner = {"x": x + 3, "y": y + 3, "w": w - 6, "h": hh - 6} if head == "none" else {"x": x + 3, "y": y + head_h + 5, "w": w - 6, "h": hh - head_h - 8}
            for k in squarify([{"n": k, "v": w_of(k)} for k in n["children"]], inner["x"], inner["y"], inner["w"], inner["h"]):
                lay(k["n"], k, gi)
            for k in n["children"]:
                if w_of(k) == 0:
                    out.append({"k": "gone", "n": k})

        if len(s["nodes"]) > 1:
            for i, rct in enumerate(squarify([{"n": n, "v": w_of(n)} for n in s["nodes"]], g["x"], g["y"], g["w"], h)):
                lay(rct["n"], rct, i)
            for n in s["nodes"]:
                if w_of(n) == 0:
                    out.append({"k": "gone", "n": n})
        else:
            lay(s["nodes"][0], {"x": g["x"], "y": g["y"], "w": g["w"], "h": h}, 0)
        return out

    leaves: list[dict] = []

    def collect(n: dict) -> None:
        if n.get("children"):
            for c2 in n["children"]:
                collect(c2)
        elif (n.get("value") or 0) > 0:
            leaves.append(n)

    for n in s["nodes"]:
        collect(n)
    weight = {id(n): n["value"] for n in leaves}

    def spread(p: list[dict]) -> float:
        ratios = [q["w"] * q["h"] / q["n"]["value"] for q in p if q["k"] == "leaf" and (q["n"].get("value") or 0) > 0]
        return max(ratios) / min(ratios) if ratios else 1

    placed = plan(weight)
    best = {"placed": placed, "err": spread(placed)}
    for _ in range(12):
        if best["err"] <= 1.01:
            break
        drawn: dict = {}
        for q in placed:
            if q["k"] == "leaf":
                drawn[id(q["n"])] = q["w"] * q["h"]
        area = sum(drawn.get(id(n), 0) for n in leaves)
        value = sum(n["value"] for n in leaves)
        if not (area > 0):
            break
        for n in leaves:
            want = n["value"] * area / value
            got = drawn.get(id(n), 0)
            weight[id(n)] = weight[id(n)] * (want / got if got > 0 else 2)
        placed = plan(weight)
        err = spread(placed)
        if err < best["err"] - 1e-9:
            best = {"placed": placed, "err": err}
    placed = best["placed"]

    small: list[str] = []
    shades = (0.1, 0.2, 0.3)

    def shade_of(gi: int) -> float:
        return shades[gi % 3]

    def label(cell: dict, host: int, ink: str, on: dict, node_id: str | None = None) -> bool:
        n = cell["n"]
        val = _value_text(n.get("value") or 0, s)
        inner = {"w": cell["w"] - 10, "h": cell["h"] - 6}
        name_ls = c.wrap(n["label"], inner["w"], True)
        val_ls = c.wrap(val, inner["w"], True)
        tries = [
            [*({"t": t, "bold": False} for t in name_ls), {"t": val, "bold": True}],
            [*({"t": t, "bold": False} for t in name_ls), *({"t": t, "bold": True} for t in val_ls)],
            [{"t": f"{n['label']} {val}", "bold": False}],
            [{"t": t, "bold": True} for t in val_ls],
        ]
        for ls in tries:
            if len(ls) * lh + 4 > inner["h"] or any(c.tw(l["t"], l["bold"]) > inner["w"] for l in ls):
                continue
            base = cell["y"] + (cell["h"] - len(ls) * lh) / 2 + size
            for k, l in enumerate(ls):
                c.text(l["t"], cell["x"] + cell["w"] / 2, base + k * lh, "middle", ink, {"bold": l["bold"], "host": host, "on": on, "of": node_id})
            return True
        return False

    leaf_no = 0
    for q in placed:
        n = q["n"]
        if q["k"] == "gone":
            small.append(f"{n['label']} {_value_text(_total_of(n), s)}")
            continue
        if q["k"] == "leaf":
            node_id = n.get("id")
            if node_id is not None:
                key = node_id
            else:
                key = f"#{leaf_no}"
                leaf_no += 1
            solid_tone = n.get("tone")
            op = None if solid_tone else shade_of(q["gi"])
            rect_opts: dict = {"fill": solid_tone or "accent", "id": node_id, "of": key, "solid": node_id if node_id is not None else f'cell "{n["label"]}"'}
            if op is not None:
                rect_opts["op"] = op
            host = c.rect(q["x"], q["y"], q["w"], q["h"], rect_opts)
            ink = "bg" if solid_tone else ink_on_shade(op)
            on: dict = {"fill": solid_tone or "accent", "ink": ink}
            if op is not None:
                on["op"] = op
            if not label(q, host, ink, on, key):
                small.append(f"{n['label']} {_value_text(n.get('value') or 0, s)}")
            continue
        c.rect(r1(q["x"]), r1(q["y"]), r1(q["w"]), r1(q["h"]), {"fill": "bg", "stroke": "border", "sw": 2, "id": n.get("id"), "of": n.get("id")})
        if q["head"] != "none":
            host = c.rect(r1(q["x"] + 2), r1(q["y"] + 2), r1(q["w"] - 4), head_h, {"fill": "code", "solid": f'header of "{n["label"]}"', "of": n.get("id")})
            text = f"{n['label']} {_value_text(_total_of(n), s)}" if q["head"] == "full" else n["label"]
            c.text(text, q["x"] + 8, c.mid(q["y"] + 2 + head_h / 2), "start", "text", {"bold": True, "host": host, "of": n.get("id")})
        if q["head"] != "full":
            small.append(f"{n['label']} {_value_text(_total_of(n), s)}")
    if s["strict"] and small:
        fail("treemap", f"{len(small)} label{'s do' if len(small) > 1 else ' does'} not fit ({', '.join(small[:3])}{', ...' if len(small) > 3 else ''}): raise width / height, or drop strict")
    c.omitted.extend(small)
    return c.done()


def treemap_band(tree, opts: dict | None = None) -> ChartBand:
    """lib/charts-dsl.ts:76-82 treemapBand() + lib/dsl/charts.ts's treemap()."""
    opts = opts or {}
    spec = resolve_treemap(tree, opts)
    ids: list[str] = []

    def walk(n: dict) -> None:
        if n.get("id"):
            ids.append(n["id"])
        for c in n.get("children") or []:
            walk(c)

    for n in spec["nodes"]:
        walk(n)
    alt = opts.get("alt") if opts.get("alt") is not None else treemap_alt(spec)
    return ChartBand(kind="treemap", spec=spec, alt=alt, **common_chart_opts("treemap", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
