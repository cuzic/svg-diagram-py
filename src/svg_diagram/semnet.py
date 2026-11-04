"""Port of lib/semnet.ts and lib/semnet-dsl.ts — pert() and dependencyNetwork(). causalLoop()
itself (lib/semnet-causal.ts + lib/semnet-ring.ts + lib/semnet-interventions.ts) lives in
semnet_causal.py; `semnet_texts()`'s `kind == 'causal'` branch delegates to its `causal_texts()`,
mirroring lib/semnet.ts's own `causalTexts` re-export from semnet-causal.ts.

Dispatched through charts.py's layout_chart()/render_chart() (the shared "chart" band
machinery every chart kind already goes through), with `kind` 'pert'/'dependency'/'causal'.

Golden master: lib/semnet.ts + lib/semnet-dsl.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import text_width
from .charts_base import ChartBand, StrokeOpts, check_ids, check_text, common_chart_opts, fail, finite_num, num_text
from .semnet_analysis import analyze_critical_path
from .semnet_causal import causal_texts
from .semnet_common import arrow, direction, head_box, network_canvas, node_box, path_of, place_edge_label, straighten_of, validate_nodes

__all__ = [
    "resolve_pert", "resolve_dependency", "pert_alt", "dependency_alt", "semnet_texts",
    "layout_pert", "layout_dependency", "pert_band", "dependency_band",
]


def resolve_pert(tasks: list[dict], *, direction_: str | None = None, unit: str | None = None, compact: bool | None = None, straighten: bool | None = None, id: str | None = None) -> dict:
    """lib/semnet.ts:25 resolvePert()."""
    analysis = analyze_critical_path(tasks)
    check_ids("pert", [t["id"] for t in tasks], id)
    return {
        "tasks": [{**t, "predecessors": list(t.get("predecessors") or [])} for t in tasks],
        "analysis": analysis,
        "direction": direction("pert", direction_),
        "unit": unit or "",
        "compact": bool(compact),
        "straighten": straighten_of("pert", straighten),
    }


def resolve_dependency(nodes: list[dict], edges: list[dict], *, direction_: str | None = None, node_kinds: dict | None = None, edge_types: dict | None = None, straighten: bool | None = None, id: str | None = None) -> dict:
    """lib/semnet.ts:30 resolveDependency()."""
    validate_nodes("dependencyNetwork", nodes, id)
    ids = {n["id"] for n in nodes}
    for i, e in enumerate(edges):
        if e["from"] not in ids or e["to"] not in ids:
            fail("dependencyNetwork", f"edges[{i}] {e['from']} -> {e['to']} names unknown node")
        check_text("dependencyNetwork", f"edges[{i}].type", e.get("type"))
        if e.get("weight") is not None:
            finite_num("dependencyNetwork", f"edges[{i}].weight", e["weight"], min=0)
    return {
        "nodes": [dict(n) for n in nodes],
        "edges": [dict(e) for e in edges],
        "direction": direction("dependencyNetwork", direction_),
        "nodeKinds": dict(node_kinds or {}),
        "edgeTypes": dict(edge_types or {}),
        "straighten": straighten_of("dependencyNetwork", straighten),
    }


def pert_alt(s: dict) -> str:
    """lib/semnet.ts:37 pertAlt()."""
    a = s["analysis"]
    tasks_desc = "; ".join(
        f"{t['label']}: duration {num_text(t['duration'])}, ES {num_text(t['es'])}, EF {num_text(t['ef'])}, LS {num_text(t['ls'])}, LF {num_text(t['lf'])}, slack {num_text(t['slack'])}" for t in a["tasks"]
    )
    return f"PERT network. Project duration {num_text(a['duration'])}{s['unit']}. Critical path: {' → '.join(a['criticalPath'])}. {tasks_desc}"


def dependency_alt(s: dict) -> str:
    """lib/semnet.ts:38 dependencyAlt()."""
    parts = []
    for e in s["edges"]:
        weight_part = "" if e.get("weight") is None else f", weight {num_text(e['weight'])}"
        parts.append(f"{e['from']} {e['type']} {e['to']}{weight_part}")
    return f"Dependency network. {'; '.join(parts)}"


def semnet_texts(kind: str, spec: dict) -> list[tuple[str, int]]:
    """lib/semnet.ts:40-46 semnetTexts()."""
    if kind == "pert":
        s = spec
        out: list[tuple[str, int]] = []
        for t in s["analysis"]["tasks"]:
            out.append((t["label"], 700))
            if s["compact"]:
                out.append((f"{num_text(t['duration'])}{s['unit']} / 余裕 {num_text(t['slack'])}", 400))
            else:
                out.append((f"ES {num_text(t['es'])}", 400))
                out.append((f"EF {num_text(t['ef'])}", 400))
                out.append((f"LS {num_text(t['ls'])}", 400))
                out.append((f"LF {num_text(t['lf'])}", 400))
                out.append((f"期間 {num_text(t['duration'])}{s['unit']} ・ 余裕 {num_text(t['slack'])}", 700 if t["critical"] else 400))
        return out
    if kind == "causal":
        return causal_texts(spec)
    s = spec
    kinds = list(dict.fromkeys(n["kind"] for n in s["nodes"] if n.get("kind")))
    types = list(dict.fromkeys(e["type"] for e in s["edges"]))
    out = [(n["label"], 700) for n in s["nodes"]]
    for e in s["edges"]:
        label = e.get("label") or s["edgeTypes"].get(e["type"], e["type"])
        w = "" if e.get("weight") is None else num_text(e["weight"])
        out.append((" ".join(x for x in (label, w) if x), 400))
    for k in kinds:
        out.append((s["nodeKinds"].get(k, k), 400))
    for t in types:
        out.append((s["edgeTypes"].get(t, t), 400))
    return out


def _kind_tone(i: int) -> str:
    return ("accent", "danger", "muted", "text")[i % 4]


def _edge_style(edge_type: str, ti: int) -> StrokeOpts:
    """How an edge type is drawn; the legend uses the same style."""
    stroke = "danger" if edge_type == "blocks" else _kind_tone(ti)
    if edge_type == "uses":
        dash = "8,5"
    elif edge_type == "relates":
        dash = "2,5"
    elif edge_type == "blocks":
        dash = "10,4,2,4"
    elif ti > 3:
        dash = "8,5" if ti % 2 else "2,5"
    else:
        dash = None
    return {"stroke": stroke, "dash": dash}


def layout_pert(s: dict, g: dict) -> dict:
    """lib/semnet.ts:55 layoutPert()."""
    w, h = (126, 64) if s["compact"] else (154, 104)
    ns = [{"id": t["id"], "label": t["label"], "w": max(w, text_width(g["widthOf"], t["label"], g["size"], 700) + 24), "h": h} for t in s["analysis"]["tasks"]]
    es = [{"from": p, "to": t["id"]} for t in s["analysis"]["tasks"] for p in t["predecessors"]]
    net = network_canvas(g, ns, es, s["direction"], 0, s["straighten"])
    c, positions, paths = net["c"], net["positions"], net["paths"]
    for i, e in enumerate(es):
        critical = any(x["from"] == e["from"] and x["to"] == e["to"] for x in s["analysis"]["criticalEdges"])
        arrow(c, path_of(paths, i, e, positions), {"stroke": "danger" if critical else "muted", "sw": 4 if critical else 2, "edge": e})
    for t in s["analysis"]["tasks"]:
        p = positions[t["id"]]
        host = node_box(c, p, t["id"], t["label"], "danger" if t["critical"] else "text", t["critical"])
        cx = p["x"] + p["w"] / 2
        c.text(t["label"], cx, p["y"] + g["size"] + 8, "middle", "text", {"bold": True, "host": host, "of": t["id"]})
        if s["compact"]:
            c.text(f"{num_text(t['duration'])}{s['unit']} / 余裕 {num_text(t['slack'])}", cx, p["y"] + p["h"] - 10, "middle", "danger" if t["critical"] else "muted", {"host": host, "of": t["id"]})
        else:
            y = p["y"] + 2 * g["size"] + 14
            left, right = p["x"] + 9, p["x"] + p["w"] - 9
            c.text(f"ES {num_text(t['es'])}", left, y, "start", "muted", {"host": host, "of": t["id"]})
            c.text(f"EF {num_text(t['ef'])}", right, y, "end", "muted", {"host": host, "of": t["id"]})
            c.text(f"LS {num_text(t['ls'])}", left, y + c.line_h(), "start", "muted", {"host": host, "of": t["id"]})
            c.text(f"LF {num_text(t['lf'])}", right, y + c.line_h(), "end", "muted", {"host": host, "of": t["id"]})
            c.text(f"期間 {num_text(t['duration'])}{s['unit']} ・ 余裕 {num_text(t['slack'])}", cx, p["y"] + p["h"] - 8, "middle", "danger" if t["critical"] else "text", {"bold": t["critical"], "host": host, "of": t["id"]})
    return c.done()


def layout_dependency(s: dict, g: dict) -> dict:
    """lib/semnet.ts:72 layoutDependency()."""
    kinds = list(dict.fromkeys(n["kind"] for n in s["nodes"] if n.get("kind")))
    types = list(dict.fromkeys(e["type"] for e in s["edges"]))
    # legend: node kinds then edge types, wrapped into rows that fit the width
    items = [{"kind": True, "key": k, "i": i, "label": s["nodeKinds"].get(k, k)} for i, k in enumerate(kinds)] + [{"kind": False, "key": t, "i": i, "label": s["edgeTypes"].get(t, t)} for i, t in enumerate(types)]
    row_h = g["size"] + 10
    rows: list[list[dict]] = []
    used = math.inf
    for it in items:
        item_w = (20 if it["kind"] else 28) + text_width(g["widthOf"], it["label"], g["size"], 400) + 18
        if used + item_w - 18 > g["w"] - 8:
            rows.append([])
            used = 0
        rows[-1].append(it)
        used += item_w
    legend_h = (34 + (len(rows) - 1) * row_h) if rows else 0
    ns = [{**n, "w": max(116, text_width(g["widthOf"], n["label"], g["size"], 700) + 28), "h": 52} for n in s["nodes"]]
    net = network_canvas(g, ns, s["edges"], s["direction"], legend_h, s["straighten"])
    c, positions, paths = net["c"], net["positions"], net["paths"]
    # two stages: every line and box first, then the labels over them (a label drawn before a later edge's line would be struck through)
    drawn: list[dict] = []
    for i, e in enumerate(s["edges"]):
        sw = 2 if e.get("weight") is None else min(7, 1.5 + math.sqrt(e["weight"]))
        path = path_of(paths, i, e, positions)
        arrow(c, path, {**_edge_style(e["type"], types.index(e["type"])), "sw": sw, "edge": e}, e["type"] != "relates")
        drawn.append({"e": e, "path": path, "head": [] if e["type"] == "relates" else [head_box(path, sw)]})
    heads = [h for d in drawn for h in d["head"]]
    for n in s["nodes"]:
        p = positions[n["id"]]
        ki = kinds.index(n["kind"]) if n.get("kind") else -1
        tone = "text" if ki < 0 else _kind_tone(ki)
        host = node_box(c, p, n["id"], n["label"], tone)
        c.text(n["label"], p["x"] + p["w"] / 2, c.mid(p["y"] + p["h"] / 2), "middle", "text", {"bold": True, "host": host, "of": n["id"]})
    for d in drawn:
        e, path = d["e"], d["path"]
        label = e.get("label") or s["edgeTypes"].get(e["type"], e["type"])
        w = "" if e.get("weight") is None else num_text(e["weight"])
        text = " ".join(x for x in (label, w) if x)
        # a label with no room is left out, as before (it does not change what the figure says, and stopping would break charts that draw today)
        place_edge_label(
            c, text, path,
            lambda m: [{"x": m["x"], "y": m["y"] - 6, "anchor": "middle"}, {"x": m["x"], "y": m["y"] + g["size"] + 8, "anchor": "middle"}, {"x": m["x"] + 12, "y": m["y"] - 6, "anchor": "start"}],
            "text", {"plate": True}, heads,
        )
    for r, row in enumerate(rows):
        x = c.x + 4
        base = c.y + c.h - 5 - (len(rows) - 1 - r) * row_h
        for it in row:
            if it["kind"]:
                c.rect(x, base - g["size"] + 2, 14, 10, {"fill": "bg", "stroke": _kind_tone(it["i"]), "sw": 2})
                x += 20
            else:
                c.line(x, base - 4, x + 22, base - 4, _edge_style(it["key"], it["i"]))
                x += 28
            c.text(it["label"], x, base, "start", "text")
            x += c.tw(it["label"]) + 18
    return c.done()


def pert_band(
    tasks: list[dict], *, direction: str | None = None, unit: str | None = None, compact: bool | None = None, straighten: bool | None = None, alt: str | None = None,
    id: str | None = None, width: float | None = None, height: float | None = None, label_role: str | None = None, reveal: int | None = None, until: int | None = None,
) -> ChartBand:
    """lib/semnet-dsl.ts:7 pertBand()."""
    spec = resolve_pert(tasks, direction_=direction, unit=unit, compact=compact, straighten=straighten, id=id)
    return ChartBand(kind="pert", spec=spec, alt=alt or pert_alt(spec), **common_chart_opts("pert", id=id, width=width, height=height, label_role=label_role, reveal=reveal, until=until))


def dependency_band(
    nodes: list[dict], edges: list[dict], *, direction: str | None = None, node_kinds: dict | None = None, edge_types: dict | None = None, straighten: bool | None = None, alt: str | None = None,
    id: str | None = None, width: float | None = None, height: float | None = None, label_role: str | None = None, reveal: int | None = None, until: int | None = None,
) -> ChartBand:
    """lib/semnet-dsl.ts:9 dependencyBand()."""
    spec = resolve_dependency(nodes, edges, direction_=direction, node_kinds=node_kinds, edge_types=edge_types, straighten=straighten, id=id)
    return ChartBand(kind="dependency", spec=spec, alt=alt or dependency_alt(spec), **common_chart_opts("dependencyNetwork", id=id, width=width, height=height, label_role=label_role, reveal=reveal, until=until))
