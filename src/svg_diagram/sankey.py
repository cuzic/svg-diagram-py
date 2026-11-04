"""1:1 port of lib/charts-sankey.ts's layoutSankey() (exported, golden-tested live via
charts.layout_chart()'s dispatch) and the sankey() DSL constructor (lib/charts-dsl.ts's
sankeyBand()) — defaults + the structural validations that affect layout.

Node icons (SankeyNode.icon) are NOT supported: icon resolution is Node's "shell" (I/O —
lib/icon-registry.ts), the same scope decision box({icon}) already made for this port. A
node's `icon` is simply never set here, so `iconOf()` is always 0 and no icon item is ever
produced.

sankeyTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
heatmapTexts()/barsTexts(): this port measures per-call, not in a pre-pass.

Golden master: lib/charts-sankey.ts + lib/charts-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .charts_base import Canvas, ChartBand, check_text, common_chart_opts, fail, finite_num, num_text
from .charts_base import _to_precision as to_precision
from .emit_common import js_num, js_round, round1


def _val(v: float, s: dict) -> str:
    return f"{num_text(to_precision(v, 12))}{s['unit']}"


def _flow_of(s: dict, id_: str) -> float:
    return max(
        sum(l["value"] for l in s["links"] if l["to"] == id_),
        sum(l["value"] for l in s["links"] if l["from"] == id_),
    )


def layers_of(s: dict) -> dict:
    """lib/charts-sankey.ts:55-70 layersOf(): the layer of each node (the longest path from a
    source; a cycle raises). Sinks go to the last layer unless align is 'left'."""
    layer: dict[str, int] = {}
    state: dict[str, int] = {}

    def into(id_: str) -> list[str]:
        return [l["from"] for l in s["links"] if l["to"] == id_]

    def visit(id_: str, trail: list[str]) -> int:
        if state.get(id_) == 2:
            return layer[id_]
        if state.get(id_) == 1:
            idx = trail.index(id_)
            cycle = [*trail[idx:], id_]
            fail("sankey", f"the links form a cycle ({' -> '.join(cycle)}); a sankey flows one way")
        state[id_] = 1
        preds = into(id_)
        l = max([-1, *[visit(p, [*trail, id_]) for p in preds]]) + 1
        state[id_] = 2
        layer[id_] = l
        return l

    for n in s["nodes"]:
        visit(n["id"], [])
    last = max(layer.values())
    if s["align"] == "justify":
        for n in s["nodes"]:
            if not any(l["from"] == n["id"] for l in s["links"]):
                layer[n["id"]] = last
    return layer


def sankey_alt(s: dict) -> str:
    """lib/charts-sankey.ts:73-76 sankeyAlt()."""
    by_id = {n["id"]: n for n in s["nodes"]}
    parts = [f"{by_id[l['from']]['label']} → {by_id[l['to']]['label']} {_val(l['value'], s)}" for l in s["links"]]
    return f"サンキー図: {'、'.join(parts)}"


def resolve_sankey(nodes: list, links: list[dict], opts: dict) -> dict:
    """lib/charts-sankey.ts:27-53 resolveSankey()."""
    if not isinstance(nodes, list) or len(nodes) < 2:
        fail("sankey", "needs at least two nodes")
    if len(nodes) > 40:
        fail("sankey", f"{len(nodes)} nodes are too many for one figure (at most 40)")
    if not isinstance(links, list) or len(links) < 1:
        fail("sankey", "needs at least one link")
    ns = []
    for n in nodes:
        if isinstance(n, str):
            ns.append({"id": n, "label": n, "tone": "text"})
        else:
            node_id = check_text("sankey", "a node id", n["id"])
            ns.append({"id": node_id, "label": n.get("label") if n.get("label") is not None else n["id"], "tone": n.get("tone") or "text"})
    ids: set[str] = set()
    id_order: list[str] = []
    for n in ns:
        check_text("sankey", f"node \"{n['id']}\"'s label", n["label"])
        if n["id"] in ids:
            fail("sankey", f'node id "{n["id"]}" is used twice')
        ids.add(n["id"])
        id_order.append(n["id"])
    if opts.get("id") is not None and opts["id"] in ids:
        fail("sankey", f'the band\'s id "{opts["id"]}" is also a node\'s id — each id must be unique')
    seen: set[str] = set()
    ls = []
    for i, l in enumerate(links):
        if l["from"] not in ids:
            fail("sankey", f'link {i + 1}: unknown node "{l["from"]}" (declared: {", ".join(id_order)})')
        if l["to"] not in ids:
            fail("sankey", f'link {i + 1}: unknown node "{l["to"]}" (declared: {", ".join(id_order)})')
        if l["from"] == l["to"]:
            fail("sankey", f'link {i + 1}: "{l["from"]}" flows into itself')
        key = f"{l['from']}>{l['to']}"
        if key in seen:
            fail("sankey", f'link {i + 1}: "{l["from"]}" -> "{l["to"]}" is given twice (add the values into one link)')
        seen.add(key)
        value = finite_num("sankey", f"link {i + 1}'s value", l["value"])
        if not (value > 0):
            fail("sankey", f'link {i + 1} ("{l["from"]}" -> "{l["to"]}"): value must be > 0 (got {l["value"]})')
        if l.get("tone") is not None and l["tone"] not in ("accent", "danger", "muted"):
            fail("sankey", f"link {i + 1}: tone must be accent, danger or muted")
        ls.append({"from": l["from"], "to": l["to"], "value": value, "tone": l.get("tone") or "accent"})
    for n in ns:
        if not any(l["from"] == n["id"] or l["to"] == n["id"] for l in ls):
            fail("sankey", f'node "{n["id"]}" has no link (leave it out, or link it)')
    spec = {"nodes": ns, "links": ls, "unit": opts.get("unit") or "", "align": opts.get("align") or "justify", "linkLabels": opts.get("linkLabels") is not False}
    layers_of(spec)  # a cycle is an error now, not at layout
    return spec


def layout_sankey(s: dict, g: dict) -> dict:
    """lib/charts-sankey.ts:84-172 layoutSankey()."""
    size = g["size"]
    c = Canvas(g["x"], g["y"], g["w"], 100, size, g["widthOf"], g["wrap"])
    lh = c.line_h()

    r1 = round1

    layer = layers_of(s)
    layer_count = max(layer.values()) + 1
    cols: list[list[str]] = [[] for _ in range(layer_count)]
    for n in s["nodes"]:
        cols[layer[n["id"]]].append(n["id"])

    pos: dict[str, int] = {}
    for col in cols:
        for i, id_ in enumerate(col):
            pos[id_] = i

    def bary(id_: str, side: str) -> float:
        ws = [l for l in s["links"] if (l["to"] == id_ if side == "in" else l["from"] == id_)]
        if not ws:
            return pos[id_]
        num = sum(pos.get(l["from"] if side == "in" else l["to"], 0) * l["value"] for l in ws)
        den = sum(l["value"] for l in ws)
        return num / den

    for _ in range(4):
        for direction in ("in", "out"):
            order = range(layer_count) if direction == "in" else range(layer_count - 1, -1, -1)
            for li in order:
                col = cols[li]
                before = {id_: i for i, id_ in enumerate(col)}
                col.sort(key=lambda a: (bary(a, direction), before[a]))
                for i, id_ in enumerate(col):
                    pos[id_] = i

    node_w = 14

    def name_of(id_: str) -> dict:
        return next(n for n in s["nodes"] if n["id"] == id_)

    def icon_of(id_: str) -> float:
        return 0  # icon support out of scope, see module docstring

    last_natural = max(c.tw(f"{name_of(id_)['label']} {_val(_flow_of(s, id_), s)}", True) + icon_of(id_) for id_ in cols[layer_count - 1])
    right_pad = min(last_natural, g["w"] * 0.24) + 14
    left_pad = 4
    plot_l = g["x"] + left_pad
    plot_r = g["x"] + g["w"] - right_pad
    step = (plot_r - node_w - plot_l) / (layer_count - 1) if layer_count > 1 else 0
    if layer_count > 1 and step < node_w + 60:
        fail("sankey", f"{layer_count} layers do not fit in {js_round(g['w'])}px (raise width, or use fewer layers)")

    def label_w(li: int) -> float:
        return right_pad - 14 if li == layer_count - 1 else step - node_w - 16

    labels: dict[str, list[str]] = {}
    for n in s["nodes"]:
        li = layer[n["id"]]
        full = f"{n['label']} {_val(_flow_of(s, n['id']), s)}"
        w = label_w(li) - icon_of(n["id"])
        one = [full] if c.tw(full, True) <= w else [*c.wrap(n["label"], w, True), _val(_flow_of(s, n["id"]), s)]
        for l in one:
            if c.tw(l, True) > w + 1:
                fail("sankey", f'the label "{l}" does not fit between the layers (shorten it, or raise width)')
        labels[n["id"]] = one

    gap = max(10, size * 0.8)

    def min_h(id_: str) -> float:
        return len(labels[id_]) * lh + 4

    max_count = max(len(col) for col in cols)
    big_h = (g["height"] if g.get("height") is not None else max(300, 46 * max_count + 120)) - 8
    c.h = big_h + 8

    def fits(sc: float) -> bool:
        return all(sum(max(_flow_of(s, id_) * sc, min_h(id_)) for id_ in col) + (len(col) - 1) * gap <= big_h for col in cols)

    lo, hi = 0.0, big_h / min(_flow_of(s, n["id"]) for n in s["nodes"]) + 1
    if not fits(0):
        fail("sankey", f"a layer has too many nodes for {big_h}px (raise height, or fewer nodes)")
    for _ in range(60):
        mid = (lo + hi) / 2
        if fits(mid):
            lo = mid
        else:
            hi = mid
    sc = lo * 0.999

    def slot(id_: str) -> float:
        return max(_flow_of(s, id_) * sc, min_h(id_))

    geo: dict[str, dict] = {}
    for li, col in enumerate(cols):
        used = sum(slot(id_) for id_ in col) + (len(col) - 1) * gap
        y = g["y"] + 4 + (big_h - used) / 2
        for id_ in col:
            nh = max(2, _flow_of(s, id_) * sc)
            geo[id_] = {"x": plot_l + li * step, "y": y + (slot(id_) - nh) / 2, "h": nh}
            y += slot(id_) + gap

    def centre(id_: str) -> float:
        return geo[id_]["y"] + geo[id_]["h"] / 2

    out_off: dict[str, float] = {}
    in_off: dict[str, float] = {}
    out_at: dict[str, float] = {}
    in_at: dict[str, float] = {}
    for l in sorted(s["links"], key=lambda l: centre(l["to"])):
        out_off[f"{l['from']}>{l['to']}"] = out_at.get(l["from"], 0)
        out_at[l["from"]] = out_at.get(l["from"], 0) + l["value"] * sc
    for l in sorted(s["links"], key=lambda l: centre(l["from"])):
        in_off[f"{l['from']}>{l['to']}"] = in_at.get(l["to"], 0)
        in_at[l["to"]] = in_at.get(l["to"], 0) + l["value"] * sc

    ribbons = []
    for l in s["links"]:
        a, b = geo[l["from"]], geo[l["to"]]
        t = l["value"] * sc
        k = f"{l['from']}>{l['to']}"
        x0, x1 = a["x"] + node_w, b["x"]
        y0, y1 = a["y"] + out_off[k], b["y"] + in_off[k]
        xm = (x0 + x1) / 2
        ribbons.append({"l": l, "t": t, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "xm": xm})

    for r in ribbons:
        x0, y0, x1, y1, xm, t = r["x0"], r["y0"], r["x1"], r["y1"], r["xm"], r["t"]

        def p(v: float) -> str:
            return js_num(r1(v))

        d = f"M{p(x0)},{p(y0)} C{p(xm)},{p(y0)} {p(xm)},{p(y1)} {p(x1)},{p(y1)} L{p(x1)},{p(y1 + t)} C{p(xm)},{p(y1 + t)} {p(xm)},{p(y0 + t)} {p(x0)},{p(y0 + t)} Z"
        tone = r["l"]["tone"]
        path_opts: dict = {"of": [r["l"]["from"], r["l"]["to"]], "fill": "accent" if tone == "accent" else tone, "op": 0.22}
        if tone == "danger":
            path_opts["stroke"] = "danger"
            path_opts["sw"] = 2
            path_opts["dash"] = "6,4"
        c.path(d, path_opts)

    for n in s["nodes"]:
        q = geo[n["id"]]
        c.rect(r1(q["x"]), r1(q["y"]), node_w, r1(q["h"]), {"fill": n["tone"], "id": n["id"], "of": n["id"], "solid": n["id"]})
        ls = labels[n["id"]]
        cy = q["y"] + q["h"] / 2
        c.lines(ls, q["x"] + node_w + 8 + icon_of(n["id"]), cy - (len(ls) - 1) * lh / 2 + size * 0.36, "start", "text", {"bold": len(ls) == 1, "of": n["id"], "plate": True})

    if s["linkLabels"]:
        for r in ribbons:
            text = _val(r["l"]["value"], s)
            cy = (r["y0"] + r["y1"]) / 2 + r["t"] / 2
            if abs(_flow_of(s, r["l"]["from"]) - r["l"]["value"]) < 1e-9 or abs(_flow_of(s, r["l"]["to"]) - r["l"]["value"]) < 1e-9:
                continue
            label = f"{name_of(r['l']['from'])['label']} → {name_of(r['l']['to'])['label']} {text}"
            if r["t"] < size + 6:
                c.omitted.append(label)
                continue
            if not c.place(text, [{"x": r["xm"], "y": c.mid(cy), "anchor": "middle"}], "text", {"bold": True, "plate": True}):
                c.omitted.append(label)

    return c.done()


def sankey_band(nodes: list, links: list[dict], opts: dict | None = None) -> ChartBand:
    """lib/charts-dsl.ts:84-88 sankeyBand() + lib/dsl/charts.ts's sankey()."""
    opts = opts or {}
    spec = resolve_sankey(nodes, links, opts)
    alt = opts.get("alt") if opts.get("alt") is not None else sankey_alt(spec)
    return ChartBand(kind="sankey", spec=spec, alt=alt, **common_chart_opts("sankey", id=opts.get("id"), width=opts.get("width"), height=opts.get("height"), label_role=opts.get("labelRole"), reveal=opts.get("reveal"), until=opts.get("until")))
