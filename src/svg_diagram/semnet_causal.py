"""1:1 port of lib/semnet-causal.ts: causalLoop() — the loops, the interventions acting on
them, and the signs/delay-marks/loop-names placed over the finished lines.

Golden master: lib/semnet-causal.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
from collections.abc import Callable

from .atoms import text_width
from .charts_base import ArrowOpts, Canvas, ChartBand, check_ids, check_text, common_chart_opts, fail
from .semnet_analysis import analyze_causal_loops
from .semnet_common import (
    arrow,
    direction,
    head_box,
    network_canvas,
    node_box,
    path_of,
    place_edge_label,
    place_plated,
    straighten_of,
    touches_any,
    validate_nodes,
)
from .semnet_interventions import band_inset, plan_interventions, ring_side
from .semnet_ring import check_ring, layout_ring

POLARITIES = ("+", "-", "same", "opposite")


def resolve_interventions(lst: list | None, nodes: list[dict], band_id: str | None) -> list[dict]:
    """lib/semnet-causal.ts:34-56 resolveInterventions()."""
    if lst is None:
        return []
    if not isinstance(lst, list):
        fail("causalLoop", "interventions must be an array")
    node_ids = {n["id"] for n in nodes}
    iv_ids = {v.get("id") if isinstance(v, dict) else None for v in lst}
    out: list[dict] = []
    for i, v in enumerate(lst):
        if not isinstance(v, dict):
            fail("causalLoop", f"interventions[{i}] must be an object {{id, label, to, polarity}}")
        check_text("causalLoop", f"interventions[{i}].id", v.get("id"))
        check_text("causalLoop", f"intervention \"{v['id']}\"'s label", v.get("label"))
        to_raw = v.get("to")
        if isinstance(to_raw, str):
            to = [to_raw]
        elif isinstance(to_raw, list):
            to = list(to_raw)
        else:
            fail("causalLoop", f'intervention "{v["id"]}": to must be a node id or an array of node ids')
            to = []
        if not to:
            fail("causalLoop", f'intervention "{v["id"]}": to needs at least one node id')
        ids: list[str] = []
        for k, t in enumerate(to):
            if not isinstance(t, str):
                fail("causalLoop", f'intervention "{v["id"]}": to[{k}] must be a node id (got {t})')
            if t not in node_ids and t in iv_ids:
                fail("causalLoop", f'intervention "{v["id"]}": an intervention cannot act on the intervention "{t}" (to takes node ids; intervention -> intervention is not supported)')
            if t not in node_ids:
                fail("causalLoop", f'intervention "{v["id"]}": to names unknown node "{t}" (nodes: {", ".join(n["id"] for n in nodes)})')
            if to.index(t) != k:
                fail("causalLoop", f'intervention "{v["id"]}": to lists node "{t}" twice')
            ids.append(t)
        if v.get("polarity") not in POLARITIES:
            fail("causalLoop", f'intervention "{v["id"]}" has invalid polarity "{v.get("polarity")}" (+, -, same or opposite; it is required)')
        if v.get("delay") is not None and not isinstance(v["delay"], bool):
            fail("causalLoop", f'intervention "{v["id"]}": delay must be true or false')
        out.append({"id": v["id"], "label": v["label"], "to": ids, "polarity": v["polarity"], "delay": bool(v.get("delay"))})
    check_ids("causalLoop", [n["id"] for n in nodes] + [v["id"] for v in out], band_id)
    return out


def resolve_causal(
    nodes: list[dict], links: list[dict], *,
    direction_: str | None = None, interventions: list | None = None, layout: str | None = None,
    straighten: bool | None = None, id: str | None = None,
) -> dict:
    """lib/semnet-causal.ts:57-63 resolveCausal()."""
    validate_nodes("causalLoop", nodes, id)
    loops = analyze_causal_loops([n["id"] for n in nodes], links)
    layout = layout or "layered"
    if layout not in ("layered", "ring"):
        fail("causalLoop", f"layout must be 'layered' or 'ring' (got {layout})")
    if layout == "ring":
        check_ring(nodes, links, loops, direction_)
    return {
        "nodes": [dict(n) for n in nodes],
        "links": [dict(e) for e in links],
        "loops": loops,
        "direction": direction("causalLoop", direction_),
        "interventions": resolve_interventions(interventions, nodes, id),
        "layout": layout,
        "straighten": straighten_of("causalLoop", straighten),
    }


def causal_band(
    nodes: list[dict], links: list[dict], *,
    direction: str | None = None, interventions: list | None = None, layout: str | None = None, straighten: bool | None = None, alt: str | None = None,
    id: str | None = None, width: float | None = None, height: float | None = None, label_role: str | None = None, reveal: int | None = None, until: int | None = None,
) -> ChartBand:
    """lib/semnet-dsl.ts:8 causalBand()."""
    spec = resolve_causal(nodes, links, direction_=direction, interventions=interventions, layout=layout, straighten=straighten, id=id)
    return ChartBand(kind="causal", spec=spec, alt=alt or causal_alt(spec), **common_chart_opts("causalLoop", id=id, width=width, height=height, label_role=label_role, reveal=reveal, until=until))


def loop_names(loops: list[dict]) -> list[str]:
    """lib/semnet-causal.ts:65 loopNames(): R1, R2, B1, ...: loops are numbered within their kind."""
    n = {"R": 0, "B": 0}
    out = []
    for l in loops:
        n[l["kind"]] += 1
        out.append(f"{l['kind']}{n[l['kind']]}")
    return out


def sign_text(p: str) -> str:
    """lib/semnet-causal.ts:66 signText()."""
    return "+" if p == "same" else "-" if p == "opposite" else p


def causal_alt(s: dict) -> str:
    """lib/semnet-causal.ts:67-71 causalAlt()."""
    names = loop_names(s["loops"])

    def label(node_id: str) -> str:
        return next((n["label"] for n in s["nodes"] if n["id"] == node_id), node_id)

    iv = ""
    if s["interventions"]:
        parts = []
        for v in s["interventions"]:
            delayed = ", delayed" if v["delay"] else ""
            parts.append(f"{v['label']} -> {', '.join(label(t) for t in v['to'])} ({sign_text(v['polarity'])}{delayed})")
        iv = f" Interventions: {'; '.join(parts)}."
    loops_text = "; ".join(f"{names[i]}: {' → '.join(l['nodes'])}" for i, l in enumerate(s["loops"])) or "No loops."
    return f"Causal loop diagram. {loops_text}{iv}"


def causal_texts(s: dict) -> list[tuple[str, int]]:
    """lib/semnet-causal.ts:72 causalTexts()."""
    out: list[tuple[str, int]] = [(n["label"], 700) for n in s["nodes"]]
    for e in s["links"]:
        out.append((sign_text(e["polarity"]), 700))
        if e.get("delay"):
            out.append(("||", 700))
        if e.get("label"):
            out.append((e["label"], 400))
    out.extend((n, 700) for n in loop_names(s["loops"]))
    for v in s["interventions"]:
        out.append((v["label"], 700))
        out.append((sign_text(v["polarity"]), 700))
        if v["delay"]:
            out.append(("||", 700))
    return out


def layout_causal(s: dict, g: dict) -> dict:
    """lib/semnet-causal.ts:74-116 layoutCausal(): stage 1 draws every line and every box
    (nodes, interventions); stage 2 places the signs/delay-marks/loop-names over the
    finished lines (placing a sign before a later edge's line would get struck through)."""
    ns = [{**n, "w": max(116, text_width(g["widthOf"], n["label"], g["size"], 700) + 28), "h": 48} for n in s["nodes"]]
    loop = next((l for l in s["loops"] if len(l["nodes"]) > 1), None) if s["layout"] == "ring" else None
    selfs = [{"index": i, "node": e["from"]} for i, e in enumerate(s["links"]) if e["from"] == e["to"]]
    items = [{"id": v["id"], "label": v["label"], "to": v["to"], "w": text_width(g["widthOf"], v["label"], g["size"], 700) + 28} for v in s["interventions"]]

    def side_of(it: dict) -> str:
        if loop is not None:
            return ring_side(loop["nodes"], it["to"])
        return "left" if s["direction"] == "TB" else "top"

    attempt = 0
    plan: dict | None = None
    laid: dict = {}
    while True:
        def has(side: str) -> list[dict]:
            return [it for it in items if side_of(it) == side]

        def inset(side: str) -> float:
            h = has(side)
            return band_inset(side, h, attempt) if h else 0

        if loop is not None:
            laid = layout_ring(g, ns, loop, selfs, {"top": inset("top"), "bottom": inset("bottom")} if items else None)
        else:
            net = network_canvas(g, ns, s["links"], s["direction"], 28, s["straighten"], {"top": inset("top"), "left": inset("left")} if items else None)
            laid = {**net, "centre": None}
        if not items:
            break
        plan = plan_interventions(laid["c"], items, laid["positions"], side_of)
        if "placed" in plan:
            break
        if attempt == 3:
            fail("causalLoop", f"{plan['problem']} (even with a thicker band; shorten the intervention labels, name fewer targets, or give the loop more room with a larger width)")
        attempt += 1

    c, positions, paths, centre = laid["c"], laid["positions"], laid["paths"], laid["centre"]
    edges: list[dict] = []
    for i, e in enumerate(s["links"]):
        p = path_of(paths, i, e, positions)
        opts: ArrowOpts = {"stroke": "text", "dash": None}
        if s["layout"] != "ring":
            opts["edge"] = e
        arrow(c, p, opts)
        edges.append({"e": e, "p": p})
    for n in s["nodes"]:
        p = positions[n["id"]]
        host = node_box(c, p, n["id"], n["label"], "text")
        c.text(n["label"], p["x"] + p["w"] / 2, c.mid(p["y"] + p["h"] / 2), "middle", "text", {"bold": True, "host": host, "of": n["id"]})
    # the interventions: a dashed box (an anchor, like a node) and a dashed arrow to each target
    iv_edges: list[dict] = []
    placed_list = plan["placed"] if plan is not None and "placed" in plan else []
    for pl in placed_list:
        item, box, arrows = pl["item"], pl["box"], pl["arrows"]
        v = next(x for x in s["interventions"] if x["id"] == item["id"])
        host = c.rect(box["x"], box["y"], box["w"], box["h"], {"fill": "bg", "stroke": "accent", "sw": 2, "dash": "6,4", "id": v["id"], "of": v["id"], "solid": f'intervention "{v["label"]}"'})
        c.text(v["label"], box["x"] + box["w"] / 2, c.mid(box["y"] + box["h"] / 2), "middle", "text", {"bold": True, "host": host, "of": v["id"]})
        for a in arrows:
            arrow(c, a["path"], {"stroke": "accent", "dash": "6,4"})
            e2 = {"from": v["id"], "to": a["to"], "polarity": v["polarity"]}
            if v["delay"]:
                e2["delay"] = True
            iv_edges.append({"e": e2, "p": a["path"]})
    heads = [head_box(ed["p"]) for ed in [*edges, *iv_edges]]
    # what changes the meaning first (polarities, then delays), then the loop names, and the free text labels last
    # on a ring the first spots are straight out of / into the ring from the arc, where there is always room
    def radial(m: dict, text: str, bold: bool = True) -> list[dict]:
        if centre is None:
            return []
        dx, dy = m["x"] - centre["x"], m["y"] - centre["y"]
        length = math.hypot(dx, dy) or 1
        ux, uy = dx / length, dy / length
        d = 13 + abs(ux) * c.tw(text, bold) / 2
        return [{"x": m["x"] + k * ux * d, "y": c.mid(m["y"] + k * uy * 13), "anchor": "middle"} for k in (1, -1)]

    no_radial: Callable[..., list[dict]] = lambda *_args, **_kwargs: []  # noqa: E731
    for ed in edges:
        place_polarity(c, g, ed["e"], ed["p"], heads, radial)
    for ed in edges:
        if ed["e"].get("delay"):
            place_delay(c, g, ed["e"], ed["p"], heads, radial)
    for ed in iv_edges:
        place_polarity(c, g, ed["e"], ed["p"], heads, no_radial)
    for ed in iv_edges:
        if ed["e"].get("delay"):
            place_delay(c, g, ed["e"], ed["p"], heads, no_radial)
    place_loop_names(c, g, s["loops"], positions, heads, centre)
    for ed in edges:
        if ed["e"].get("label"):
            place_label(c, g, ed["e"]["label"], ed["p"], heads, radial)
    return c.done()


Radial = Callable[..., list[dict]]


def _sign_of(e: dict) -> str:
    return sign_text(e["polarity"])


def no_room(what: str, e: dict) -> None:
    """lib/semnet-causal.ts:121 noRoom(): a polarity or a delay mark that finds no room stops
    the build: without it the figure says something else (R reads as B). More height or
    width does not help, the room is beside the edge."""
    fail("causalLoop", f"{what} of {e['from']} -> {e['to']} has no room (the figure is too dense around this link: drop a link or a node, or shorten the node labels; a larger height / width does not make room)")


def place_polarity(c: Canvas, g: dict, e: dict, p: list[dict], heads: list[dict], radial: Radial) -> None:
    """lib/semnet-causal.ts:123-126 placePolarity()."""
    sign = _sign_of(e)
    ok = place_edge_label(
        c, sign, p,
        lambda m: [*radial(m, sign), {"x": m["x"], "y": m["y"] - 6, "anchor": "middle"}, {"x": m["x"], "y": m["y"] + g["size"] + 8, "anchor": "middle"}, {"x": m["x"] + 12, "y": m["y"] - 6, "anchor": "start"}],
        "danger" if sign == "-" else "accent", {"bold": True, "plate": True}, heads,
    )
    if not ok:
        no_room(f'the polarity "{sign}"', e)


def place_delay(c: Canvas, g: dict, e: dict, p: list[dict], heads: list[dict], radial: Radial) -> None:
    """lib/semnet-causal.ts:127-129 placeDelay()."""
    ok = place_edge_label(
        c, "||", p,
        lambda m: [*radial(m, "||"), {"x": m["x"], "y": m["y"] + g["size"] + 8, "anchor": "middle"}, {"x": m["x"] + 14, "y": m["y"] + g["size"] + 8, "anchor": "start"}],
        "muted", {"bold": True, "plate": True}, heads,
    )
    if not ok:
        no_room('the delay mark "||"', e)


def place_label(c: Canvas, g: dict, text: str, p: list[dict], heads: list[dict], radial: Radial) -> None:
    """lib/semnet-causal.ts:131-133 placeLabel(): an edge's free text label; left out when
    there is no room (it does not change what the figure says)."""
    place_edge_label(
        c, text, p,
        lambda m: [*radial(m, text, False), {"x": m["x"] + 12, "y": m["y"] - 6, "anchor": "start"}, {"x": m["x"], "y": m["y"] + g["size"] + 8, "anchor": "middle"}],
        "text", {"plate": True}, heads,
    )


def place_loop_names(c: Canvas, g: dict, loops: list[dict], positions: dict[str, dict], heads: list[dict], centre: dict | None = None) -> None:
    """lib/semnet-causal.ts:135-145 placeLoopNames(): R1 / B1 under the loop's lowest node;
    when a sign is already there: above the loop, at its centre, then outwards in 8px steps."""
    names = loop_names(loops)
    for i, l in enumerate(loops):
        ps = [positions[node_id] for node_id in l["nodes"]]
        x = sum(p["x"] + p["w"] / 2 for p in ps) / len(ps)
        bottom = max(p["y"] + p["h"] for p in ps)
        top = min(p["y"] for p in ps)
        home = {"x": x, "y": min(c.y + c.h - 5, bottom + g["size"] + 6), "anchor": "middle"}
        cands: list[dict] = [
            home,
            {"x": x, "y": top - 6, "anchor": "middle"},
            {"x": x, "y": c.mid(sum(p["y"] + p["h"] / 2 for p in ps) / len(ps)), "anchor": "middle"},
        ]
        if centre is not None and len(l["nodes"]) > 1:
            cands.insert(0, {"x": centre["x"], "y": c.mid(centre["y"]), "anchor": "middle"})
        for k in range(1, 13):
            for dx, dy in ((0, k), (0, -k), (k, 0), (-k, 0)):
                cands.append({**home, "x": x + dx * 8, "y": home["y"] + dy * 8})
        name = names[i]
        tone = "accent" if l["kind"] == "R" else "danger"
        placed = place_plated(c, name, cands, tone, {"bold": True, "plate": True}, lambda b, heads=heads: not touches_any(b, heads))
        if placed is None:
            c.text(name, home["x"], home["y"], "middle", tone, {"bold": True, "plate": True})
