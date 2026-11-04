"""1:1 port of lib/toc.ts's causeTree() side: layout_cause_band/layout_cause_band_once (the
Theory-of-Constraints cause tree: Current/Future Reality Tree, Prerequisite Tree, Transition
Tree, PDPC and Why-Why Tree are all this one figure) + the DSL constructor causeBand(), ported
here as cause_band() — the shared validator/builder causeTree()/pdpc()/relationDiagram() all
go through on the Node side. pdpc()/relationDiagram()/whyWhyTree()/transitionUnits()/
prerequisiteTree()/transitionTree()/negativeBranchTree() are NOT ported: they only call
causeBand()/causeTree() with different defaults or pre-shape nodes/links (same reason other
DSL sugar is left out elsewhere in this port — causeTree() is the one function that actually
draws anything). `causeTexts()` (text pre-registration) is not ported either, same reason as
bpmnTexts()/classesTexts()/statesTexts().

lib/toc.ts's cloud() side (the Evaporating Cloud) already lives in cloud.py (ported in an
earlier session) — see that module instead.

Golden master: lib/toc.ts + lib/toc-analysis.ts + lib/emit-figures.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
from collections import deque

from .cause_clash import and_clashes
from .cause_hop import HOP_R, cause_crossings
from .emit_boxes import render_box_rect
from .emit_common import arrow_path, emoji_span, js_round, snap4
from .fit_width import fit_layout
from .layered_route import gap_for, layered_attempt
from .polyline_metrics import score_of
from .tokens import PALETTE, color_of, resolve_box_style, tone_style
from .toc_analysis import core_drivers, reach_counts
from .tree_text import measure_node, node_runs
from .verify_base import routes_through_nodes

GAP, LEVEL, PORT = 28, 64, 22
CORE_BADGE_H, CORE_BADGE_W, CORE_BADGE_GAP = 22, 44, 2
AND_END, AND_PEAK, AND_REACH = 21, 15, 10

CAUSE_ROLES: dict[str, dict] = {
    "effect": {"tone": "plain"},
    "ude": {"tone": "danger"},
    "root": {"tone": "accent", "double": True},
    "de": {"tone": "new"},
    "injection": {"tone": "changed"},
    "goal": {"tone": "accent", "double": True},
    "obstacle": {"tone": "plain"},  # drawn as a hexagon
    "io": {"tone": "new"},
    "action": {"tone": "changed"},
    "start": {"tone": "accent", "double": True},
    "step": {"tone": "plain"},
    "risk": {"tone": "danger"},  # drawn as a hexagon
    "measure": {"tone": "changed"},
    "precondition": {"tone": "removed"},
    "tipping": {"tone": "danger", "double": True},
    "trim": {"tone": "changed", "dashed": True},
    "need": {"tone": "solid"},
}

_ROLE_TAGS = {"root": "根本原因", "goal": "ゴール", "injection": "施策", "start": "開始"}


def _swap(p: dict) -> dict:
    return {"x": p["y"], "y": p["x"]}


def causes_of(l: dict) -> list[str]:
    """lib/toc.ts:60 causesOf(): the ids a link's `from` names, as a list."""
    f = l["from"]
    return [f] if isinstance(f, str) else list(f)


def _sgn(v: float) -> int:
    if abs(v) < 0.5:  # a last run a hair off the straight (float noise) is still straight
        return 0
    return (v > 0) - (v < 0)


def and_ends(g: dict, points_of) -> dict:
    """lib/toc.ts:63-72 andEnds(): the last run of each arrow of an AND, when they can carry
    one arc (see below): the arrows arrive on one side, all heading the same way, with room
    before the head for the arc."""
    ends = [{"tip": pts[-1], "prev": pts[-2]} for pts in (points_of(k) for k in g["arrows"])]
    first = ends[0]
    d = {"x": _sgn(first["tip"]["x"] - first["prev"]["x"]), "y": _sgn(first["tip"]["y"] - first["prev"]["y"])}

    def along(p: dict) -> float:
        return p["x"] if d["x"] else p["y"]

    def cross(p: dict) -> float:
        return p["y"] if d["x"] else p["x"]

    aligned = all(
        _sgn(e["tip"]["x"] - e["prev"]["x"]) == d["x"] and _sgn(e["tip"]["y"] - e["prev"]["y"]) == d["y"] and abs(along(e["tip"]) - along(first["tip"])) < 1
        for e in ends
    )
    room = min(abs(along(e["tip"]) - along(e["prev"])) for e in ends)
    return {"ends": ends, "d": d, "along": along, "cross": cross, "ok": aligned and room >= AND_END + 1}


def layout_cause_band_once(
    band: dict, x: float, y: float, w: float, width_of, roles: dict, env: dict,
    height_budget: float | None = None, canvas_bound: bool = False,
    another_order: list[str] | None = None, plain_routes: bool = False, no_detour: bool = False,
    _asided_out: dict | None = None,
) -> dict:
    """lib/toc.ts:71-82(layoutCauseBand)/82-305(layoutCauseBandOnce, the part that is not the
    order search — see layout_cause_band_at for that) ported together: validates `band`,
    builds the arrows/AND groups, measures and lays the nodes out (layered_attempt over
    fit_layout's direction/width search), then draws nodes/edges/AND-arcs/hop crossings into
    a plain LaidOutCause-shaped dict. `_asided_out`: Python-only — when given a dict, this
    call writes {"asided": bool} into it (mirrors lib/toc.ts's module-level `movedAside`
    WeakSet, scoped per call instead of relying on object identity across calls)."""
    ids: set[str] = set()
    for n in band["nodes"]:
        if not isinstance(n.get("id"), str) or not n["id"]:
            raise ValueError("causeTree(): every node needs an id")
        if not isinstance(n.get("label"), str) or not n["label"].strip():
            raise ValueError(f'causeTree(): node "{n["id"]}" needs a label')
        if n["id"] in ids:
            raise ValueError(f'causeTree(): duplicate node id "{n["id"]}"')
        ids.add(n["id"])

    # one arrow per cause of a link; an AND (several causes) is a group, remembered by its effect
    arrows: list[dict] = []
    groups: list[dict] = []
    pairs: set[str] = set()
    for l in band["links"]:
        froms = causes_of(l)
        if not froms:
            raise ValueError(f'causeTree(): a link to "{l["to"]}" has no cause')
        if l["to"] not in ids:
            raise ValueError(f'causeTree(): a link names unknown node "{l["to"]}"')
        if l.get("back") is not None and (l["back"] is not True or not isinstance(l["from"], str)):
            kind_desc = f"back {l['back']}" if isinstance(l["from"], str) else "a list of causes (an AND)"
            raise ValueError(f'causeTree(): link to "{l["to"]}" has back: true with {kind_desc}; a return is one arrow from one cause')
        group: dict | None = {"to": l["to"], "arrows": []} if len(froms) > 1 else None
        for f in froms:
            if f not in ids:
                raise ValueError(f'causeTree(): link {f} -> {l["to"]} names unknown node "{f}"')
            if f == l["to"]:
                raise ValueError(f'causeTree(): "{f}" cannot be its own cause')
            pair_key = f"{f}\x00{l['to']}"
            if pair_key in pairs:
                raise ValueError(f'causeTree(): link {f} -> {l["to"]} is written twice')
            pairs.add(pair_key)
            arrow: dict = {"from": f, "to": l["to"], "line": "dashed" if l.get("kind") == "blocks" else (l.get("line") or "solid")}
            if l.get("back"):
                arrow["back"] = True
            if l.get("kind") == "blocks":
                arrow["blocks"] = True
            k = len(arrows)
            arrows.append(arrow)
            if group is not None:
                group["arrows"].append(k)
        if group is not None:
            groups.append(group)

    # ALAP (ADR 0019 D1): the entities where a cause starts stay on the first layer; the input side moves up to its effects
    layer_mode = band.get("layer") or ("alap" if band.get("tree") in ("prt", "frt", "tt", "nbr") else "asap")
    if band.get("layerFrom") == "effect":
        alap: dict | None = {"keep": []}
    elif layer_mode == "alap":
        alap = {"keep": [n["id"] for n in band["nodes"] if n.get("role") in ("root", "injection", "start")]}
    else:
        alap = None
    # the 中核 badge sits outside the frame, at the end of the axis the arrows run along (H7)
    has_core = any(n.get("core") for n in band["nodes"])

    def pad_of(vertical: bool) -> dict:
        if not has_core:
            return {"x": 0, "y": 0}
        return {"x": 0, "y": CORE_BADGE_H + CORE_BADGE_GAP} if vertical else {"x": CORE_BADGE_W + CORE_BADGE_GAP, "y": 0}

    space_val = env.get("space")
    space_or_1 = space_val if space_val is not None else 1

    def build(dir_: str, max_w: float, floor: bool, fold: float | None = None) -> dict:
        vertical = dir_ in ("up", "down")
        flip = dir_ in ("up", "left")
        iw = w - 2 * pad_of(vertical)["x"]
        lines = {n["id"]: measure_node(n["label"], n.get("sub"), max_w, width_of, roles, env["wrap"], floor) for n in band["nodes"]}
        order: list[str] = []

        def put(node_id: str) -> None:
            if node_id not in order:
                order.append(node_id)

        by_id = {n["id"]: n for n in band["nodes"]}
        written = [by_id[nid] for nid in another_order] if another_order is not None else band["nodes"]
        for n in written:
            put(n["id"])
            for g in groups:
                if any(arrows[k]["from"] == n["id"] for k in g["arrows"]):
                    for k in g["arrows"]:
                        put(arrows[k]["from"])
        ranked = [by_id[i] for i in order]

        def degree_of(node_id: str) -> int:
            return max(sum(1 for a in arrows if a["from"] == node_id), sum(1 for a in arrows if a["to"] == node_id))

        degree = max([1, *(degree_of(n["id"]) for n in band["nodes"])])

        real: dict[str, dict] = {}
        for n in band["nodes"]:
            l = lines[n["id"]]
            need = 12 + (degree_of(n["id"]) - 1) * PORT
            real[n["id"]] = {"w": max(l["w"], need), "h": l["h"]} if vertical else {"w": l["w"], "h": max(l["h"], need)}
        hex_ids = {n["id"] for n in band["nodes"] if n.get("role") in ("obstacle", "risk")}
        lr_nodes = [{"id": n["id"], "size": ({"w": real[n["id"]]["h"], "h": real[n["id"]]["w"]} if vertical else real[n["id"]])} for n in ranked]
        group_index: dict[int, int] = {}
        for gi, g in enumerate(groups):
            for k in g["arrows"]:
                group_index[k] = gi

        def place_in(total: dict):
            def place(p: dict) -> dict:
                q = _swap(p) if vertical else dict(p)
                if flip:
                    if vertical:
                        q["y"] = total["h"] - q["y"]
                    else:
                        q["x"] = total["w"] - q["x"]
                return {"x": q["x"] + x + pad_of(vertical)["x"] + (iw - total["w"]) / 2, "y": q["y"] + y + pad_of(vertical)["y"]}

            return place

        declared = [k for k, a in enumerate(arrows) if a.get("back")]
        if band.get("returns") == "inline":
            wanted = None
        elif (band.get("returns") or band.get("returnsDefault")) == "outer":
            wanted = "all"
        elif declared:
            wanted = "declared"
        else:
            wanted = None

        def loose_of(rts: dict, ly: dict) -> list[str]:
            route: dict[int, list[dict]] = {}
            for i, e in enumerate(ly["edges"]):
                if not e.get("self"):
                    route[e["index"]] = rts[i]
            return [g["to"] for g in groups if not and_ends(g, lambda k: route[k])["ok"]]

        def attempt_with(returns: str | None) -> dict:
            layout_opts: dict = {
                "dir": "right",
                "gap": js_round(GAP * space_or_1),
                "levelGap": max(js_round(LEVEL * space_or_1), gap_for(degree, 0, space_or_1)),
            }
            if declared:
                layout_opts["back"] = declared
            if alap:
                layout_opts["alap"] = alap
            if fold is not None:
                layout_opts["fold"] = fold
            o: dict = {
                "portStep": PORT,
                "groupOf": lambda k: group_index.get(k),
                "round": lambda node_id: node_id in hex_ids,
                "transpose": vertical,
                "maxAcross": iw + 0.5,
                "place": place_in,
                "looseOf": loose_of,
            }
            if space_val is not None and space_val != 1:
                o["space"] = space_val
            if returns:
                o["returns"] = returns
            if band.get("straighten") is False:
                o["straighten"] = False
            if not (band.get("straighten") is False or no_detour):
                o["detour"] = True
            if plain_routes:
                o["aside"] = False
            elif band.get("straighten") is not False:
                o["apart"] = True
            return layered_attempt(lr_nodes, [{"from": a["from"], "to": a["to"]} for a in arrows], layout_opts, o)

        attempt = attempt_with(wanted)
        # not written: the outer lanes give way when they do not fit the width or leave an AND undrawable that the inline run draws
        if wanted and band.get("returns") is None and any(e.get("outer") for e in attempt["lay"]["edges"]):
            inline = attempt_with(None)
            if not attempt["fits"] or len(attempt["loose"]) > len(inline["loose"]):
                attempt = inline
        pad = pad_of(vertical)
        return {
            **attempt,
            "size": {"w": attempt["size"]["w"] + 2 * pad["x"], "h": attempt["size"]["h"] + 2 * pad["y"]},
            "dir": dir_,
            "vertical": vertical,
            "flip": flip,
            "lines": lines,
        }

    # What may change to make the figure fit (ADR 0010 D1): only what the author left out (`dir`, `maxNodeW`) or gave as 'auto'
    base = band.get("base") or "up"
    explicit_dir = band.get("dir") is not None and band["dir"] != "auto" and not band.get("dirLeftOut")
    start = base if band.get("dir") is None or band.get("dir") == "auto" else band["dir"]
    plan: dict = {
        "who": "whyWhyTree()" if band.get("layerFrom") == "effect" else "causeTree()",
        "w": w,
        "start": start,
        "keepWords": env.get("keepWords"),
        "explicitDir": explicit_dir,
        "mode": "auto" if band.get("dir") == "auto" else "omitted",
        "build": build,
        "layoutOf": lambda r: {"lay": r["lay"], "vertical": r["vertical"]},
    }
    if band.get("base") is not None:
        plan["alt"] = "right"
    else:
        plan["axisKept"] = f"another axis (a cause tree keeps its direction: {start})"
    if band.get("maxNodeW") is not None and band["maxNodeW"] != "auto":
        plan["maxNodeW"] = band["maxNodeW"]
    if band.get("maxNodeW") == "auto":
        plan["autoWidth"] = True
    if band.get("base") is None and band.get("layerFrom") != "effect":
        plan["foldable"] = True
        if band.get("fold") is not None:
            plan["fold"] = band["fold"]
    plan["best"] = band.get("base") is not None and band.get("dir") == "auto"
    if height_budget is not None:
        plan["heightBudget"] = height_budget - (y if (band.get("maxNodeW") == "auto" and canvas_bound) else 0)
    if band.get("returns") == "outer":
        plan["notTried"] = ["returns: 'inline' (returns is written: 'outer')"]
    fitted = fit_layout(plan)
    attempt = fitted["result"]
    lines, vertical, flip, fit_applied = attempt["lines"], attempt["vertical"], attempt["flip"], fitted["applied"]
    lay, routes = attempt["lay"], attempt["routes"]

    pad = pad_of(vertical)
    total = {"w": attempt["size"]["w"] - 2 * pad["x"], "h": attempt["size"]["h"] - 2 * pad["y"]}
    dx = x + pad["x"] + (w - 2 * pad["x"] - total["w"]) / 2
    dy = y + pad["y"]

    def rect_of(node_id: str) -> dict:
        p = lay["nodes"][node_id]
        q = {"x": p["y"], "y": p["x"], "w": p["h"], "h": p["w"]} if vertical else {"x": p["x"], "y": p["y"], "w": p["w"], "h": p["h"]}
        if flip:
            if vertical:
                q["y"] = total["h"] - (q["y"] + q["h"])
            else:
                q["x"] = total["w"] - (q["x"] + q["w"])
        return {"x": q["x"] + dx, "y": q["y"] + dy, "w": q["w"], "h": q["h"]}

    out: dict = {"type": "cause", "x": x, "y": y, "w": w, "h": total["h"] + 2 * pad["y"]}
    if band.get("id") is not None:
        out["id"] = band["id"]
    if band.get("reveal") is not None:
        out["reveal"] = band["reveal"]
    if band.get("unanchored"):
        out["unanchored"] = band["unanchored"]
    if band.get("until") is not None:
        out["until"] = band["until"]
    out.update({"nodes": [], "edges": [], "ands": [], "loose": attempt["loose"], "texts": [], "anchors": [], "labelBoxes": []})
    if fit_applied:
        out["fitApplied"] = fit_applied
    if band.get("tree") == "nbr":
        out["nbr"] = {"vertical": vertical}
    if _asided_out is not None:
        _asided_out["asided"] = bool(attempt.get("asided"))

    for n in band["nodes"]:
        r = rect_of(n["id"])
        role = CAUSE_ROLES[n.get("role") or "effect"]
        node_out: dict = {**r, "tone": n.get("tone") or role["tone"]}
        if role.get("double"):
            node_out["double"] = True
        if role.get("dashed"):
            node_out["dashed"] = True
        if n.get("core"):
            node_out["core"] = True
        if n.get("role") in ("obstacle", "risk"):
            node_out["hex"] = True
        out["nodes"].append(node_out)
        out["anchors"].append({"id": n["id"], **r})
        l = lines[n["id"]]
        out["texts"].extend(node_runs({"x": r["x"] + (r["w"] - l["w"]) / 2, "y": r["y"] + (r["h"] - l["h"]) / 2, "w": l["w"]}, l, roles))
        out["labelBoxes"].append({"label": n["label"], **r})

    drawn: dict[int, int] = {}
    for i, e in enumerate(lay["edges"]):
        if e.get("self"):
            continue
        drawn[e["index"]] = len(out["edges"])
        ar = arrows[e["index"]]
        edge_out: dict = {"from": e["from"], "to": e["to"], "points": routes[i], "line": ar["line"]}
        if ar.get("back"):
            edge_out["back"] = True
        if e.get("outer"):
            edge_out["outer"] = True
        if ar.get("blocks"):
            edge_out["kind"] = "blocks"
        if band.get("hop") and e.get("reversed"):
            edge_out["reversed"] = True
        out["edges"].append(edge_out)

    # an AND: an arc across the last run of each of its arrows, a little before the arrowheads
    for g in groups:
        ends_data = and_ends(g, lambda k: out["edges"][drawn[k]]["points"])
        if not ends_data["ok"]:
            continue
        ends, d, along, cross = ends_data["ends"], ends_data["d"], ends_data["along"], ends_data["cross"]
        us = [cross(e["tip"]) for e in ends]
        tip = ends[0]["tip"]
        others = [
            cross(e["points"][-1])
            for k, e in enumerate(out["edges"])
            if e["to"] == g["to"] and not any(drawn.get(a) == k for a in g["arrows"]) and abs(along(e["points"][-1]) - along(tip)) < 1
        ]

        def reach_to(u: float, sign: int) -> float:
            candidates = [abs(o - u) / 2 - 5 for o in others if (o - u) * sign > 0]
            return max(0, min([AND_REACH, *candidates]))

        lo = min(us) - reach_to(min(us), -1)
        hi = max(us) + reach_to(max(us), 1)

        def at(u: float, dist: float) -> dict:
            return {"x": tip["x"] - d["x"] * dist, "y": u} if d["x"] else {"x": u, "y": tip["y"] - d["y"] * dist}

        out["ands"].append({
            "to": g["to"],
            "from": [arrows[k]["from"] for k in g["arrows"]],
            "p0": at(lo, AND_END),
            "c": at((lo + hi) / 2, 2 * AND_PEAK - AND_END),
            "p1": at(hi, AND_END),
        })

    # ADR 0028: where a return crosses another line, and which of those get a hop (decided here, once; the renderer only draws them)
    if band.get("hop"):
        crossings = cause_crossings(out["edges"], attempt["dir"], {"x": out["x"], "y": out["y"], "w": out["w"], "h": out["h"]}, out["nodes"], out["ands"], band["hop"] == "all")
        if crossings:
            out["crossings"] = crossings
    return out


MAX_ORDERS = 60
PATIENCE, PATIENCE_QUIET = 30, 14


def _crossings_of_cause(t: dict) -> int:
    return sum(1 for c in and_clashes(t["edges"], t["ands"]) if c["how"] == "crosses")


def _score_of_cause(t: dict) -> list[float]:
    """lib/toc.ts:224 scoreOfCause(): (AND arrows that cross, AND arrows that run side by
    side, crossings, bends) — smaller is better, in this order."""
    s = score_of([e["points"] for e in t["edges"]])
    clashes = and_clashes(t["edges"], t["ands"])
    crosses = sum(1 for c in clashes if c["how"] == "crosses")
    non_crosses = len(clashes) - crosses
    return [crosses, non_crosses, s["crossings"], s["bends"]]


def _lex_less_cause(a: list[float], b: list[float]) -> bool:
    for x, y in zip(a, b):
        if x != y:
            return x < y
    return False


def layout_cause_band_at(
    band: dict, x: float, y: float, w: float, width_of, roles: dict, env: dict,
    height_budget: float | None = None, canvas_bound: bool = False,
) -> dict:
    """lib/toc.ts:67-157 layoutCauseBandAt(): when the arrows into an effect with an AND
    cross each other, or any two arrows cross, the order the entities are written in is
    tried again in a few fixed ways (ADR 0019 D4); a figure with no crossing is never
    touched. Only a cause tree (not pdpc() / relationDiagram(), which pass `base`)."""
    asided_first: dict = {}
    first = layout_cause_band_once(band, x, y, w, width_of, roles, env, height_budget, canvas_bound, _asided_out=asided_first)

    def axis_of(t: dict) -> list[float]:
        key = "x" if band.get("dir") in ("left", "right") else "y"
        return [n[key] for n in t["nodes"]]

    if band.get("base") is not None:
        return first
    if _crossings_of_cause(first) == 0 and score_of([e["points"] for e in first["edges"]])["crossings"] == 0:
        # a crossing of any two arrows also starts the search; judged before the side-by-side runs are moved aside (D12/D13), which also clears crossings
        if not asided_first.get("asided") or _crossings_of_cause(layout_cause_band_once(band, x, y, w, width_of, roles, env, height_budget, canvas_bound, None, True)) == 0:
            return first

    ids = [n["id"] for n in band["nodes"]]
    if band.get("straighten") is False:
        base = first
    else:
        # The search scores the figures without the detours of the long arrows (slow, and the search lays a figure out up to MAX_ORDERS times)
        base = layout_cause_band_once(band, x, y, w, width_of, roles, env, height_budget, canvas_bound, None, False, True)

    orders: list[list[str]] = [list(reversed(ids))]
    for k in range(min(len(ids) - 1, 6)):
        orders.append([*ids[k + 1 :], *ids[: k + 1]])

    base_axis = axis_of(base)
    best = base
    best_score = _score_of_cause(base)
    best_order: list[str] | None = None

    seen: set[str] = {"\x00".join(ids), *("\x00".join(o) for o in orders)}
    queue: deque[list[str]] = deque(orders)

    def add(o: list[str]) -> None:
        k = "\x00".join(o)
        if k not in seen:
            seen.add(k)
            queue.append(o)

    if band.get("straighten") is not False:
        # a seeded LCG (the same figure always gets the same answer)
        seed = 20260417 + len(ids)

        def rand(n: int) -> int:
            nonlocal seed
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            return seed % n

        for _ in range(min(24, len(ids) * 3)):
            o = list(ids)
            for i in range(len(o) - 1, 0, -1):
                j = rand(i + 1)
                o[i], o[j] = o[j], o[i]
            add(o)

    tried = 0
    last_better = 0
    polished = False
    while queue or (not polished and band.get("straighten") is not False):
        if not queue:  # swaps of two neighbours of the best order, once the shuffles are done
            polished = True
            if best_score[0] == 0 and best_score[1] == 0 and best_score[2] == 0:
                break  # nothing crosses: only bends are left
            cur_order = best_order if best_order is not None else ids
            for i in range(len(cur_order) - 1):
                o = list(cur_order)
                o[i], o[i + 1] = o[i + 1], o[i]
                add(o)
            continue
        # give up when nothing has got better for a while: sooner once no AND arrows cross
        tried += 1
        if tried > MAX_ORDERS or tried - last_better > (PATIENCE_QUIET if best_score[0] == 0 else PATIENCE):
            break
        order = queue.popleft()
        try:
            t = layout_cause_band_once(band, x, y, w, width_of, roles, env, height_budget, canvas_bound, order, False, True)
        except Exception:  # noqa: BLE001 — any failure of a speculative order just means "try another"
            continue
        axis_t = axis_of(t)
        # the same layers (a different order must not change which edge of a cycle is cut, or fold the figure), the same size limits
        if any(abs(v - base_axis[i]) > 0.5 for i, v in enumerate(axis_t)) or t["h"] > base["h"] + 0.5 or len(t["loose"]) > len(base["loose"]):
            continue
        if len(t.get("fitApplied") or []) != len(base.get("fitApplied") or []):
            continue
        score = _score_of_cause(t)
        if _lex_less_cause(score, best_score):
            best, best_score, best_order, last_better = t, score, order, tried
            if polished:
                queue.clear()
                polished = False

    if band.get("straighten") is False:
        return best

    found: dict | None = None
    if best_order is not None:
        try:
            found = layout_cause_band_once(band, x, y, w, width_of, roles, env, height_budget, canvas_bound, best_order)
        except Exception:  # noqa: BLE001
            found = None

    def same_frame(t: dict) -> bool:
        axis_t = axis_of(t)
        return (
            all(abs(v - base_axis[i]) <= 0.5 for i, v in enumerate(axis_t))
            and t["h"] <= base["h"] + 0.5
            and len(t["loose"]) <= len(base["loose"])
            and len(t.get("fitApplied") or []) == len(base.get("fitApplied") or [])
        )

    # the best of: the first figure, the best order with the detours, the best figure without them (the base itself when no order beat it): the first one wins a tie
    pick = first
    pick_score = _score_of_cause(first)
    for t in (found, best):
        if t is None or not same_frame(t):
            continue
        sc = _score_of_cause(t)
        if _lex_less_cause(sc, pick_score):
            pick, pick_score = t, sc
    return pick


def layout_cause_band(
    band: dict, x: float, y: float, w: float, width_of, roles: dict, env: dict,
    height_budget: float | None = None, canvas_bound: bool = False,
) -> dict:
    """lib/toc.ts:71-80 layoutCauseBand(): `density: 'compact'` must not make an arrow run
    through a box (the check calls that an error): the narrower gaps between the layers can
    do that, so this band is drawn at the normal gaps then."""
    out = layout_cause_band_at(band, x, y, w, width_of, roles, env, height_budget, canvas_bound)
    space = env.get("space")
    if space is None or space == 1:
        return out

    def through(t: dict) -> int:
        return len(routes_through_nodes(t["edges"], t["anchors"], lambda *_: ""))

    bad = through(out)
    if bad == 0:
        return out
    # the normal gaps may not fit the width or the height that the compact figure fits: the compact figure stays then
    try:
        normal = layout_cause_band_at(band, x, y, w, width_of, roles, {**env, "space": 1}, height_budget, canvas_bound)
    except Exception:  # noqa: BLE001
        return out
    if through(normal) < bad:
        normal["densityRestored"] = True
        return normal
    return out


def cause_band(
    nodes: list[dict], links: list[dict], *,
    dir: str | None = None, max_node_w: float | str | None = None, core_driver: bool | None = None,
    role_tags: bool | dict | None = None, hop: bool | str | None = None, tree: str | None = None,
    layer: str | None = None, counts: bool | None = None, core_driver_label: str | None = None,
    returns: str | None = None, straighten: bool | None = None, fold: bool | None = None,
    alt: str | None = None, id: str | None = None, reveal: int | None = None, until: int | None = None,
    base: str | None = None,
) -> dict:
    """lib/dsl/diagrams.ts:209-253 causeBand(): causeTree()'s body (pdpc()/relationDiagram()
    pass base='down'; not ported, see module docstring). `mirrors`/`mirrorOf`/`rca`/`scope`/
    the handle & anchors DSL sugar are not ported: the first three are read only by checks
    (out of this port's scope, never by layout/render), and the DSL sugar adds non-enumerable
    properties with no effect on a rendered figure."""
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("causeTree(nodes, links) needs at least one node")
    if not isinstance(links, list):
        raise ValueError("causeTree(nodes, links): links must be an array")
    if dir is not None and dir not in ("up", "down", "right", "left", "auto"):
        raise ValueError(f"causeTree(): dir must be 'up', 'down', 'right', 'left' or 'auto' (got {dir})")
    if max_node_w is not None and max_node_w != "auto" and not (isinstance(max_node_w, (int, float)) and not isinstance(max_node_w, bool) and max_node_w >= 80 and math.isfinite(max_node_w)):
        raise ValueError(f"causeTree(): maxNodeW must be a number >= 80 or 'auto' (got {max_node_w})")
    for l in links:
        if l.get("line") is not None and l["line"] not in ("solid", "dashed", "dotted"):
            raise ValueError(f"causeTree(): link to {l['to']} has line {l.get('line')}")
    if hop is not None and not isinstance(hop, bool) and hop != "all":
        raise ValueError(f"causeTree(): hop must be true, false or 'all' (got {hop})")
    if fold is not None and not isinstance(fold, bool):
        raise ValueError(f"causeTree(): fold must be true or false (got {fold})")
    if straighten is not None and not isinstance(straighten, bool):
        raise ValueError(f"causeTree(): straighten must be true or false (got {straighten})")
    if returns is not None and returns not in ("inline", "outer"):
        raise ValueError(f"causeTree(): returns must be 'inline' or 'outer' (got {returns})")
    for l in links:
        kind = l.get("kind")
        if kind is not None and kind not in ("cause", "blocks"):
            raise ValueError(f"causeTree(): link to {l['to']} has kind {kind} (use 'cause' or 'blocks')")
        if kind == "blocks" and not isinstance(l.get("from"), str):
            raise ValueError(f"causeTree(): a 'blocks' link to {l['to']} needs one entity as its from (a string, not an AND)")
        if l.get("back") is None:
            continue
        if l["back"] is not True:
            raise ValueError(f"causeTree(): link to {l['to']} has back {l['back']} (write back: true, or leave it out)")
        if not isinstance(l.get("from"), str):
            raise ValueError(f'causeTree(): a link to "{l["to"]}" is an AND (from is a list) and also back: true. A return is one arrow: write the link that returns on its own')
    for n in nodes:
        if n.get("role") is not None and n["role"] not in CAUSE_ROLES:
            raise ValueError(f"causeTree(): node \"{n['id']}\" has role {n.get('role')} (use {', '.join(CAUSE_ROLES)})")
        if n.get("tone") is not None and n["tone"] not in ("plain", "accent", "new", "changed", "removed", "muted", "danger"):
            raise ValueError(f"causeTree(): node \"{n['id']}\" has tone {n.get('tone')}")
    if tree is not None and tree not in ("crt", "frt", "prt", "tt", "nbr"):
        raise ValueError(f"causeTree(): tree must be 'crt', 'frt', 'prt', 'tt' or 'nbr' (got {tree})")
    if layer is not None and layer not in ("asap", "alap"):
        raise ValueError(f"causeTree(): layer must be 'asap' or 'alap' (got {layer})")
    if role_tags is not None and role_tags is not True and (
        not isinstance(role_tags, dict) or any(k not in _ROLE_TAGS or not isinstance(v, str) or not v.strip() or "\n" in v or "\r" in v for k, v in role_tags.items())
    ):
        raise ValueError(f"causeTree(): roleTags is true, or an object with root / goal / injection / start, each a non-empty one-line text (got {role_tags})")
    if core_driver_label is not None and (not isinstance(core_driver_label, str) or not core_driver_label.strip() or "\n" in core_driver_label or "\r" in core_driver_label):
        raise ValueError(f"causeTree(): coreDriverLabel is a non-empty one-line text with {{n}} (the number reached) and {{total}} (the number of ude entities) (got {core_driver_label})")
    if core_driver is not None and not isinstance(core_driver, bool):
        raise ValueError(f"causeTree(): coreDriver must be true or false (got {core_driver})")
    for n in nodes:
        if n.get("foldsInto") is not None and (n.get("role") != "trim" or not isinstance(n["foldsInto"], str) or not n["foldsInto"].strip()):
            raise ValueError(f"causeTree(): node \"{n['id']}\" has foldsInto {n.get('foldsInto')!r} (foldsInto is a non-empty text, and only a role: 'trim' node takes it)")

    # foldsInto is a line under the label (added here, so that it is measured with the label); roleTags: the words in front of the author's sub line
    tag_map = {**_ROLE_TAGS, **(role_tags if isinstance(role_tags, dict) else {})} if role_tags is not None else None
    tagged = nodes
    if tag_map is not None:
        tagged = []
        for n in nodes:
            tag = tag_map.get(n.get("role"))
            tagged.append({**n, "sub": f"【{tag}】{'　' + n['sub'] if n.get('sub') else ''}"} if tag else n)
    noted = []
    for n in tagged:
        if n.get("foldsInto") is None:
            noted.append(n)
            continue
        rest = {k: v for k, v in n.items() if k != "foldsInto"}
        rest["sub"] = f"{n['sub'] + '　' if n.get('sub') else ''}→ {n['foldsInto']} に組み込む"
        noted.append(rest)

    ude_total = sum(1 for n in nodes if n.get("role") == "ude")

    def core_label(n: int) -> str:
        template = core_driver_label or "{n}/{total} 件に届く"
        return template.replace("{n}", str(n)).replace("{total}", str(ude_total))

    counted = reach_counts(nodes, links) if core_driver else None
    core = set(core_drivers(counted)) if counted is not None else set()
    marked = noted
    if counted is not None:
        marked = []
        for n in noted:
            reach = counted.get(n["id"])
            if reach is None or n.get("role") == "trim":
                marked.append(n)
                continue
            n2 = dict(n)
            if n["id"] in core:
                n2["core"] = True
            if counts is not False:
                n2["sub"] = f"{n.get('sub') + '　' if n.get('sub') else ''}{core_label(reach)}"
            marked.append(n2)

    band: dict = {"type": "cause", "nodes": list(marked), "links": [{**l, **({} if isinstance(l["from"], str) else {"from": list(l["from"])})} for l in links]}
    if dir is not None:
        band["dir"] = dir
    elif base is not None:
        band["dir"] = base
        band["dirLeftOut"] = True
    if base is not None:
        band["base"] = base
    if max_node_w is not None:
        band["maxNodeW"] = max_node_w
    if tree is not None:
        band["tree"] = tree
    if tag_map is not None:
        band["roleTags"] = tag_map
    if layer is not None:
        band["layer"] = layer
    if returns is not None:
        band["returns"] = returns
    if hop is not None:
        band["hop"] = hop
    elif tree is not None:
        band["hop"] = "all"
    if straighten is not None:
        band["straighten"] = straighten
    if fold is not None and base is None:
        band["fold"] = fold
    if id is not None:
        band["id"] = id
    if reveal is not None:
        band["reveal"] = reveal
    if until is not None:
        band["until"] = until
    return band


_CORE_STROKE = 3.5


def _core_badge(n: dict, node_id: str, b: dict, day) -> str:
    """lib/emit-figures.ts:314-324 coreBadge(): a thick frame and a small 中核 badge just
    outside the side of the box away from the arrows that leave it."""
    leave = next((e["points"][0] for e in b["edges"] if e["from"] == node_id), None)
    eps = 1
    if leave is None:
        side = "top"
    elif abs(leave["y"] - n["y"]) < eps:
        side = "bottom"
    elif abs(leave["y"] - n["y"] - n["h"]) < eps:
        side = "top"
    elif abs(leave["x"] - n["x"]) < eps:
        side = "right"
    else:
        side = "left"
    x = n["x"] - CORE_BADGE_W - CORE_BADGE_GAP if side == "left" else n["x"] + n["w"] + CORE_BADGE_GAP if side == "right" else n["x"] + 6
    y = n["y"] - CORE_BADGE_H - CORE_BADGE_GAP if side == "top" else n["y"] + n["h"] + CORE_BADGE_GAP if side == "bottom" else n["y"] + 6
    fill = PALETTE["muted"] if b.get("dim") else color_of("accent", day)
    return (
        f'<rect x="{snap4(x)}" y="{snap4(y)}" width="{CORE_BADGE_W}" height="{CORE_BADGE_H}" rx="8" fill="{fill}"/>\n  '
        f'<text x="{snap4(x + CORE_BADGE_W / 2)}" y="{snap4(y + 16)}" text-anchor="middle" font-size="14" font-weight="700" fill="{PALETTE["bg"]}">中核</text>'
    )


def render_cause(b: dict, day) -> str:
    """lib/emit-figures.ts:326-359 renderCause()."""
    out: list[str] = []
    stroke = PALETTE["muted"] if b.get("dim") else PALETTE["text"]

    def cuts_of(k: int) -> list[dict] | None:
        mine = [c for c in (b.get("crossings") or []) if not c.get("skipped") and c["over"] == k]
        return [{"x": c["x"], "y": c["y"], "side": c["side"], "r": HOP_R} for c in mine] if mine else None

    for k, e in enumerate(b["edges"]):
        if e.get("kind") == "blocks":
            out.append(arrow_path(e["points"], stroke, e["line"], 2, "end", "bar", cuts_of(k)))
        elif e.get("back"):
            out.append(arrow_path(e["points"], stroke, e["line"], 3, "end", "arrow", cuts_of(k)))
        else:
            out.append(arrow_path(e["points"], stroke, e["line"], 2, "end", "arrow", cuts_of(k)))
    # the AND arc: across the arrows of one effect, just before their heads
    for a in b["ands"]:
        out.append(f'<path d="M{snap4(a["p0"]["x"])},{snap4(a["p0"]["y"])} Q{snap4(a["c"]["x"])},{snap4(a["c"]["y"])} {snap4(a["p1"]["x"])},{snap4(a["p1"]["y"])}" fill="none" stroke="{stroke}" stroke-width="2"/>')
    for i, n in enumerate(b["nodes"]):
        if n.get("hex"):  # an obstacle: a hexagon (pointed left and right), in its tone's colours
            if b.get("dim"):
                st = {"fill": PALETTE["bg"], "stroke": PALETTE["muted"], "dashed": False}
            else:
                st = resolve_box_style(n.get("tone"), day, n.get("dashed"))
            k2 = min(16, n["h"] / 2)
            cy = n["y"] + n["h"] / 2
            corners = [(n["x"] + k2, n["y"]), (n["x"] + n["w"] - k2, n["y"]), (n["x"] + n["w"], cy), (n["x"] + n["w"] - k2, n["y"] + n["h"]), (n["x"] + k2, n["y"] + n["h"]), (n["x"], cy)]
            pts = " ".join(f"{snap4(px)},{snap4(py)}" for px, py in corners)
            sw = _CORE_STROKE if n.get("core") else 2
            dash = ' stroke-dasharray="6,4"' if st["dashed"] else ""
            out.append(f'<polygon points="{pts}" fill="{st["fill"]}" stroke="{st["stroke"]}" stroke-width="{sw}"{dash} stroke-linejoin="round"/>')
            if n.get("core"):
                out.append(_core_badge(n, b["anchors"][i]["id"], b, day))
            continue
        rect = render_box_rect(x=n["x"], y=n["y"], w=n["w"], h=n["h"], day=day, tone=n.get("tone"), dim=bool(b.get("dim")), default_tone="plain")
        out.append(rect.replace('stroke-width="2.5"', f'stroke-width="{_CORE_STROKE}"') if n.get("core") else rect)
        if n.get("double"):
            inner = render_box_rect(x=n["x"] + 4, y=n["y"] + 4, w=n["w"] - 8, h=n["h"] - 8, day=day, tone=n.get("tone"), dim=bool(b.get("dim")), default_tone="plain")
            out.append(inner.replace('rx="8"', 'rx="5"'))
        if n.get("core"):
            out.append(_core_badge(n, b["anchors"][i]["id"], b, day))

    def ink(t: dict) -> str:
        if b.get("dim"):
            return PALETTE["muted"]
        n = next((r for r in b["nodes"] if r["x"] <= t["x"] <= r["x"] + r["w"] and r["y"] < t["y"] <= r["y"] + r["h"]), None)
        if t.get("muted"):
            return PALETTE["text"] if n and tone_style(n.get("tone")).fill == "soft" else PALETTE["muted"]
        return color_of(tone_style(n.get("tone") if n else None).text, day)

    for t in b["texts"]:
        bold = ' font-weight="700"' if t.get("bold") else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}" text-anchor="middle" font-size="{t["size"]}"{bold} fill="{ink(t)}">{emoji_span(t["text"])}</text>')
    return "\n  ".join(out)
