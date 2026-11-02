"""1:1 port of lib/semnet-common.ts: what pert(), causalLoop() and dependencyNetwork() share
— the layered canvas, arrows, node boxes and the labels placed beside edges. On top of the
already-ported charts_base.py's Canvas and layered_route.py's layered_attempt().

Golden master: lib/semnet-common.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
from collections.abc import Callable

from .charts_base import Canvas, check_ids, check_text, fail, overlaps
from .emit_common import js_num, js_round
from .layered_route import layered_attempt


def straighten_of(who: str, v: bool | None) -> bool:
    """lib/semnet-common.ts:13 straightenOf()."""
    if v is not None and not isinstance(v, bool):
        fail(who, f"straighten must be true or false (got {v})")
    return v is not False


def direction(who: str, d: str | None) -> str:
    """lib/semnet-common.ts:18 direction()."""
    if d is not None and d not in ("LR", "TB"):
        fail(who, f"direction must be LR or TB (got {d})")
    return d or "LR"


def validate_nodes(who: str, nodes: list[dict], band_id: str | None = None) -> None:
    """lib/semnet-common.ts:19-23 validateNodes()."""
    if not nodes:
        fail(who, "needs at least one node")
    for i, n in enumerate(nodes):
        check_text(who, f"nodes[{i}].id", n.get("id"))
        check_text(who, f"node \"{n.get('id')}\"'s label", n.get("label"))
    check_ids(who, [n["id"] for n in nodes], band_id)


def _r(n: float) -> float:
    return js_round(n * 10) / 10


def arrow(c: Canvas, points: list[dict], opts: dict, mark: bool = True) -> None:
    """lib/semnet-common.ts:26-32 arrow(). `opts`: {stroke, sw?, dash?, of?, edge?} — `edge`
    is the edge this arrow draws (recorded in the chart's `edges`; a self-loop is not)."""
    edge = opts.get("edge")
    o = {k: v for k, v in opts.items() if k != "edge"}
    if edge and edge["from"] != edge["to"]:
        c.edges.append({"from": edge["from"], "to": edge["to"], "points": [{"x": p["x"], "y": p["y"]} for p in points]})
    for i in range(1, len(points)):
        prev, q = points[i - 1], points[i]
        c.line(prev["x"], prev["y"], q["x"], q["y"], {**o, "avoid": True})
    if len(points) < 2 or not mark:
        return
    b, a = points[-1], points[-2]
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    length = math.hypot(dx, dy) or 1
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    z = 7 + o.get("sw", 2)
    d = (
        f'M{js_num(_r(b["x"]))},{js_num(_r(b["y"]))} '
        f'L{js_num(_r(b["x"] - ux * z + px * z * 0.55))},{js_num(_r(b["y"] - uy * z + py * z * 0.55))} '
        f'L{js_num(_r(b["x"] - ux * z - px * z * 0.55))},{js_num(_r(b["y"] - uy * z - py * z * 0.55))} Z'
    )
    c.path(d, {"fill": o["stroke"], "of": o.get("of")})


def head_box(p: list[dict], sw: float = 2) -> dict:
    """lib/semnet-common.ts:34 headBox(): the box an arrow head fills (the head is drawn as a
    path, which the canvas does not register)."""
    b = p[-1]
    z = 7 + sw + 2
    return {"x": b["x"] - z, "y": b["y"] - z, "w": 2 * z, "h": 2 * z}


def edge_mid(p: list[dict]) -> dict:
    """lib/semnet-common.ts:35 edgeMid()."""
    i = max(0, math.floor((len(p) - 1) / 2))
    a, b = p[i], p[i + 1]
    return {"x": (a["x"] + b["x"]) / 2, "y": (a["y"] + b["y"]) / 2}


def path_of(paths: dict[int, list[dict]], i: int, e: dict, positions: dict[str, dict]) -> list[dict]:
    """lib/semnet-common.ts:36-40 pathOf()."""
    routed = paths.get(i)
    if routed:
        return routed
    n = positions[e["from"]]  # self loop (route_layered deliberately leaves these to the caller)
    return [
        {"x": n["x"] + n["w"], "y": n["y"] + n["h"] * 0.7},
        {"x": n["x"] + n["w"] + 24, "y": n["y"] + n["h"] * 0.7},
        {"x": n["x"] + n["w"] + 24, "y": n["y"] - 18},
        {"x": n["x"] + n["w"] * 0.7, "y": n["y"] - 18},
        {"x": n["x"] + n["w"] * 0.7, "y": n["y"]},
    ]


def place_plated(c: Canvas, text: str, cands: list[dict], fill: str, o: dict, also: Callable[[dict], bool] = lambda b: True) -> dict | None:
    """lib/semnet-common.ts:43-49 placePlated(): draws the label at the first candidate whose
    plate (2px wider than the text each side) is free, and that `also` accepts."""
    for k in cands:
        b = c.box_of(text, js_round(k["x"]), js_round(k["y"]), k["anchor"], o.get("bold", False))
        if c.free({"x": b["x"] - 2, "y": b["y"], "w": b["w"] + 4, "h": b["h"]}, o.get("host", -1), 0, True) and also(b):
            return c.text(text, k["x"], k["y"], k["anchor"], fill, o)
    return None


def _along(p: list[dict], fracs: list[float]) -> list[dict]:
    """lib/semnet-common.ts:51-58 along(): points along a polyline at fractions of its
    length, with the segment each lies on (horizontal or not) and how far it is from that
    segment's ends."""
    lens = [math.hypot(p[i + 1]["x"] - p[i]["x"], p[i + 1]["y"] - p[i]["y"]) for i in range(len(p) - 1)]
    total = sum(lens)
    out: list[dict] = []
    for f in fracs:
        d = f * total
        i = 0
        while i < len(lens) - 1 and d > lens[i]:
            d -= lens[i]
            i += 1
        ln = lens[i] if i < len(lens) else 0
        t = d / ln if ln else 0
        a, b = p[i], p[i + 1]
        out.append({"pt": {"x": a["x"] + (b["x"] - a["x"]) * t, "y": a["y"] + (b["y"] - a["y"]) * t}, "horizontal": abs(b["y"] - a["y"]) < abs(b["x"] - a["x"]), "room": min(d, ln - d)})
    return out


ON_EDGE = [0.5, 0.45, 0.55, 0.4, 0.6, 0.35, 0.65, 0.3, 0.7, 0.25, 0.75, 0.2, 0.8]


def touches_any(b: dict, boxes: list[dict]) -> bool:
    """lib/semnet-common.ts:68 touchesAny(): does the box reach any of these (arrow heads,
    say)?"""
    return any(overlaps(b, h) for h in boxes)


def place_edge_label(c: Canvas, text: str, p: list[dict], beside_at: Callable[[dict], list[dict]], fill: str, o: dict, heads: list[dict] | None = None) -> dict | None:
    """lib/semnet-common.ts:60-77 placeEdgeLabel(): the second stage of an edge label: beside
    the edge when there is room; otherwise on the edge itself, from the middle outwards."""
    heads = heads or []

    def clear(b: dict) -> bool:
        return not touches_any(b, heads)

    near = place_plated(c, text, beside_at(edge_mid(p)), fill, o, clear)
    if near is None:
        flat_cands = [cand for a in _along(p, ON_EDGE) for cand in beside_at(a["pt"])]
        near = place_plated(c, text, flat_cands, fill, o, clear)
    if near:
        return near
    w, h = c.tw(text, o.get("bold", False)), c.size + 4
    cands: list[dict] = []
    room: dict[int, float] = {}
    for a in _along(p, ON_EDGE):
        k = {"x": a["pt"]["x"], "y": c.mid(a["pt"]["y"]), "anchor": "middle"}
        cands.append(k)
        room[id(k)] = a["room"] - ((w if a["horizontal"] else h) / 2 + 2)
    for k in cands:
        if room.get(id(k), 0) < 6:
            continue
        put = place_plated(c, text, [k], fill, o, clear)
        if put:
            return put
    return None


def network_canvas(g: dict, nodes: list[dict], edges: list[dict], dir: str, legend_h: float = 0, straighten: bool = True, inset: dict | None = None) -> dict:
    """lib/semnet-common.ts:80-95 networkCanvas(). Orthogonal routing works in the layout's
    right-running axes; TB is that geometry transposed. `inset` keeps a band along one side
    free (the interventions go there); without it every number below is what it always was."""
    vertical = dir == "TB"
    inset = inset or {}
    top, left = inset.get("top") or 0, inset.get("left") or 0

    def scale_of(size: dict) -> float:
        return min(1, (g["w"] - left - 8) / max(1, size["w"]))

    def ox_of(size: dict) -> float:
        return g["x"] + left + (g["w"] - left - size["w"] * scale_of(size)) / 2

    def content_h(size: dict) -> float:
        # a `height` taller than the content leaves room: the layout sits in the middle of it (between the intervention band above and the legend below), on the 4px grid; no room, no move
        return size["h"] * scale_of(size) + 16 + legend_h + top

    def oy_of(size: dict) -> float:
        return g["y"] + 8 + top + math.floor(max(0, (g.get("height") or 0) - content_h(size)) / 2 / 4) * 4

    def place_in(size: dict) -> Callable[[dict], dict]:
        def place(p: dict) -> dict:
            scale, ox, oy = scale_of(size), ox_of(size), oy_of(size)
            return {"x": ox + p["y"] * scale, "y": oy + p["x"] * scale} if vertical else {"x": ox + p["x"] * scale, "y": oy + p["y"] * scale}

        return place

    layered_nodes = [{"id": n["id"], "size": ({"w": n["h"], "h": n["w"]} if vertical else {"w": n["w"], "h": n["h"]})} for n in nodes]
    run = layered_attempt(layered_nodes, edges, {"dir": "right", "gap": 28, "levelGap": 76}, {"transpose": vertical, "place": place_in, "tighten": True, "straighten": straighten})
    lay, paths, natural = run["lay"], run["routes"], run["size"]
    scale, ox, oy = scale_of(natural), ox_of(natural), oy_of(natural)
    positions: dict[str, dict] = {}
    for node_id, p in lay["nodes"].items():
        positions[node_id] = (
            {"x": ox + p["y"] * scale, "y": oy + p["x"] * scale, "w": p["h"] * scale, "h": p["w"] * scale}
            if vertical
            else {"x": ox + p["x"] * scale, "y": oy + p["y"] * scale, "w": p["w"] * scale, "h": p["h"] * scale}
        )
    h = max(g.get("height") or 0, natural["h"] * scale + 16 + legend_h + top)
    c = Canvas(g["x"], g["y"], g["w"], h, g["size"], g["widthOf"], g["wrap"])
    for n in nodes:
        p = positions[n["id"]]
        c.solids.append({**p, "id": n["id"], "label": f'node "{n["label"]}"'})
    return {"c": c, "positions": positions, "paths": paths}


def node_box(c: Canvas, p: dict, node_id: str, label: str, tone: str, critical: bool = False) -> int:
    """lib/semnet-common.ts:98-101 nodeBox()."""
    c.rect(p["x"], p["y"], p["w"], p["h"], {"fill": "accent" if critical else "bg", "op": 0.16 if critical else None, "stroke": tone, "sw": 4 if critical else 2, "id": node_id, "of": node_id})
    return next((i for i, s in enumerate(c.solids) if s.get("id") == node_id), -1)
