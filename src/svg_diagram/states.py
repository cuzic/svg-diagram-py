"""1:1 port of lib/states.ts's layoutStatesBand() (exported, golden-tested live) and
lib/emit-figures.ts's renderStates(): stateDiagram() and flowchart() (the same band type,
"states", with the words of the one that was called) — states/nodes and transitions/arrows
that place themselves (layered_route.py's layered_attempt(), on fit_width.py's plan_fit()
for the dir 'right'/'down' exploration). A state is a box like a tree node; a transition is
an orthogonal arrow routed through the layers it skips; a label sits on the arrow in a
white chip. flowchart() adds decisions (diamonds) and terminators (pills) via flow_nodes.py.

NOT ported: statesTexts() (a pre-registration list, same reason bpmn.py's bpmnTexts() etc.
are not ported) and a state's `icon` (the icon registry itself is not ported — box()'s
renderBoxIcon is out of scope for the same reason; states_band()/flowchart_band() raise
NotImplementedError if a state sets it).

Golden master: lib/states.ts + lib/emit-figures.ts's renderStates() (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
import re

from .atoms import text_width
from .emit_boxes import render_box_rect
from .emit_common import _sign, emoji_span, js_num, js_round, line_attrs, snap4
from .fit_width import plan_fit
from .flow_nodes import diamond_lines, onto_diamond, pill_lines, vertex_drops
from .layered_route import gap_for, layered_attempt, stub_of
from .states_words import states_words
from .tokens import PALETTE, color_of, is_solid_tone, resolve_box_style, tone_style
from .tree_text import measure_node, node_runs
from .verify_base import states_problems

STATE_ICON = 24
_ICON_H = STATE_ICON + 4  # an icon above the label: its size and a gap
_ARROW, GAP, _DOT, _LOOP, _LOOP_W, _CHIP_PAD = 14, 28, 8, 26, 12, 6
_INIT = "\x00init"

_FLOW_SHAPE = {"process": None, "decision": "diamond", "terminator": "pill"}
_FLOW_NODE_KEYS = {"id", "label", "sub", "kind", "tone", "icon"}


def _swap(p: dict) -> dict:
    return {"x": p["y"], "y": p["x"]}


def _point_at(pts: list[dict], t: float) -> dict:
    """lib/states.ts:27-36 pointAt(): the point a fraction t of the way along a polyline's
    length."""
    lens = [abs(pts[i + 1]["x"] - pts[i]["x"]) + abs(pts[i + 1]["y"] - pts[i]["y"]) for i in range(len(pts) - 1)]
    half = sum(lens) * t
    for i, ln in enumerate(lens):
        if half <= ln or i == len(lens) - 1:
            f = half / ln if ln else 0
            return {"x": pts[i]["x"] + (pts[i + 1]["x"] - pts[i]["x"]) * f, "y": pts[i]["y"] + (pts[i + 1]["y"] - pts[i]["y"]) * f}
        half -= ln
    return pts[0]


def _states_band_of(
    states: list[dict], transitions: list[dict], *, flavor: str | None, dir: str | None, initial: str | None,
    max_node_w: float | None, returns: str | None, straighten: bool | None, id: str | None,
) -> dict:
    """lib/dsl/diagrams.ts:113-130 statesBandOf()."""
    w = states_words(flavor)
    if returns is None and flavor == "flowchart":  # a flowchart goes back to a decision as often as forward: its return arrows take the lane outside the figure
        returns = "outer"
    if not states:
        raise ValueError("flowchart(nodes, edges) needs at least one node" if flavor == "flowchart" else "stateDiagram(states, transitions) needs at least one state")
    if dir is not None and dir not in ("right", "down", "auto"):
        raise ValueError(f"{w['who']}: dir must be 'right', 'down' or 'auto' (got {dir})")
    if max_node_w is not None and not (max_node_w >= 80 and math.isfinite(max_node_w)):
        raise ValueError(f"{w['who']}: maxNodeW must be a number >= 80 (got {max_node_w})")
    if straighten is not None and not isinstance(straighten, bool):
        raise ValueError(f"{w['who']}: straighten must be true or false (got {straighten})")
    if returns is not None and returns not in ("inline", "outer"):
        raise ValueError(f"{w['who']}: returns must be 'inline' or 'outer' (got {returns})")
    for t in transitions:
        if t.get("line") is not None and t["line"] not in ("solid", "dashed", "dotted"):
            raise ValueError(f"{w['who']}: {w['edge']} {t['from']} -> {t['to']} has line {t['line']}")
    for s in states:
        if s.get("tone") is not None and s["tone"] not in ("plain", "accent", "new", "changed", "removed", "muted", "danger", "solid", "solid-danger"):
            raise ValueError(f'{w["who"]}: {w["node"]} "{s["id"]}" has tone {s["tone"]} (use plain, accent, new, changed, removed, muted, danger, solid or solid-danger)')
        if s.get("shape") is not None and s["shape"] not in ("box", "circle", "diamond", "pill"):
            raise ValueError(f'{w["who"]}: {w["node"]} "{s["id"]}" has shape {s["shape"]} (use \'box\', \'circle\', \'diamond\' or \'pill\')')
        if s.get("shape") in ("diamond", "pill") and s.get("final"):
            raise ValueError(f'{w["who"]}: {w["node"]} "{s["id"]}" is a {s["shape"]} and final: the double outline is a rectangle\'s (use a box)')
        if s.get("icon") is not None:
            raise NotImplementedError(f'{w["who"]}: {w["node"]} "{s["id"]}" sets icon, but this port does not implement the icon registry (same reason box()\'s icon is out of scope)')
    by_id = {s["id"]: s for s in states}
    for t in transitions:
        s = by_id.get(t["from"])
        if t["from"] == t["to"] and s is not None and s.get("shape") in ("diamond", "pill"):
            raise ValueError(f'{w["who"]}: a {s["shape"]} cannot loop to itself ("{t["from"]}": the loop leaves from the side of a rectangle)')
        if t.get("tone") is not None and t["tone"] not in ("danger", "accent", "muted"):
            raise ValueError(f"{w['who']}: {w['edge']} {t['from']} -> {t['to']} has tone {t['tone']} (use danger, accent or muted)")

    band: dict = {"type": "states", "states": list(states), "transitions": list(transitions)}
    if flavor:
        band["flavor"] = flavor
    if dir is not None:
        band["dir"] = dir
    if initial is not None:
        band["initial"] = initial
    if max_node_w is not None:
        band["maxNodeW"] = max_node_w
    if returns is not None:
        band["returns"] = returns
    if flavor == "flowchart" and dir is None:
        band["defaultDir"] = "down"
    if straighten is not None:
        band["straighten"] = straighten
    if id is not None:
        band["id"] = id
    return band


def states_band(
    states: list[dict], transitions: list[dict], *, dir: str | None = None, initial: str | None = None,
    max_node_w: float | None = None, returns: str | None = None, straighten: bool | None = None, id: str | None = None,
) -> dict:
    """lib/dsl/diagrams.ts:108-111 stateDiagram()."""
    return _states_band_of(states, transitions, flavor=None, dir=dir, initial=initial, max_node_w=max_node_w, returns=returns, straighten=straighten, id=id)


def flowchart_band(
    nodes: list[dict], edges: list[dict], *, dir: str | None = None, max_node_w: float | None = None,
    returns: str | None = None, straighten: bool | None = None, id: str | None = None,
) -> dict:
    """lib/dsl/diagrams.ts:141-152 flowchart()."""
    if not nodes:
        raise ValueError("flowchart(nodes, edges) needs at least one node")
    items: list[dict] = []
    for n in nodes:
        extra = [k for k in n if k not in _FLOW_NODE_KEYS]
        if extra:
            raise ValueError(f'flowchart(): node "{n["id"]}" has an unknown option {", ".join(repr(k) for k in extra)} (id, label, sub, kind, tone, icon)')
        kind = n.get("kind", "process")
        if kind not in _FLOW_SHAPE:
            raise ValueError(f'flowchart(): node "{n["id"]}" has kind {kind} (use \'process\', \'decision\' or \'terminator\')')
        shape = _FLOW_SHAPE[kind]
        item = {k: v for k, v in n.items() if k != "kind"}
        if shape is not None:
            item["shape"] = shape
        items.append(item)
    return _states_band_of(items, edges, flavor="flowchart", dir=dir, initial=None, max_node_w=max_node_w, returns=returns, straighten=straighten, id=id)


def layout_states_band(band: dict, x: float, y: float, w: float, width_of, roles: dict, env: dict, height_budget: float | None = None) -> dict:
    """lib/states.ts:39-48 layoutStatesBand()."""
    out = _layout_states_band_at(band, x, y, w, width_of, roles, env, height_budget)
    if "noFit" in out:
        raise ValueError(out["failure"]())
    space = env.get("space", 1)
    if space == 1:
        return out
    # `density: 'compact'` must not make the check find more wrong in a state diagram (a label on another label or arrow, an arrow through a state): then it is drawn at the normal gaps
    bad = len(states_problems(out))
    if bad == 0:
        return out
    normal = _layout_states_band_at(band, x, y, w, width_of, roles, {**env, "space": 1}, height_budget)
    if "noFit" in normal or len(states_problems(normal)) >= bad:
        return out
    normal["densityRestored"] = True
    return normal


def _layout_states_band_at(band: dict, x: float, y: float, w: float, width_of, roles: dict, env: dict, height_budget: float | None = None) -> dict:
    """lib/states.ts:50-250 layoutStatesBandAt()."""
    S = roles["note"]
    words = states_words(band.get("flavor"))
    ids: set[str] = set()
    for s in band["states"]:
        if not isinstance(s.get("id"), str) or not s["id"] or s["id"] == _INIT:
            raise ValueError(f"{words['who']}: every {words['node']} needs an id")
        if not isinstance(s.get("label"), str) or not s["label"].strip():
            raise ValueError(f'{words["who"]}: {words["node"]} "{s["id"]}" needs a label')
        if s["id"] in ids:
            raise ValueError(f'{words["who"]}: duplicate {words["node"]} id "{s["id"]}"')
        ids.add(s["id"])
    for t in band["transitions"]:
        for e in (t["from"], t["to"]):
            if e not in ids:
                raise ValueError(f'{words["who"]}: {words["edge"]} {t["from"]} -> {t["to"]} names unknown {words["node"]} "{e}"')
    if band.get("initial") is not None and band["initial"] not in ids:
        raise ValueError(f'{words["who"]}: initial names unknown {words["node"]} "{band["initial"]}"')

    circles = {s["id"] for s in band["states"] if s.get("shape") == "circle"}  # round nodes: arrows keep to the middle of their side (ADR 0016 D3)

    def label_w(t: str) -> float:
        return math.ceil(text_width(width_of, t, S, 400)) + 2 * _CHIP_PAD

    widest = max([label_w(t["label"]) for t in band["transitions"] if t.get("label")], default=0.0)
    edges = [{"from": t["from"], "to": t["to"]} for t in band["transitions"]]
    loops = [t for t in band["transitions"] if t["from"] == t["to"]]
    # the most arrows that meet one state (each needs its own lane in the gap beside it)
    degree = max([1.0, *(max(sum(1 for t in band["transitions"] if t["from"] == s["id"] and t["from"] != t["to"]), sum(1 for t in band["transitions"] if t["to"] == s["id"] and t["from"] != t["to"])) for s in band["states"])])
    if band.get("initial"):
        edges.append({"from": _INIT, "to": band["initial"]})

    def swap_size(sz: dict) -> dict:
        return {"w": sz["h"], "h": sz["w"]}

    loop_label_h = (S + 10) if any(t.get("label") for t in loops) else 0

    # One whole attempt: the text wrapped at maxW, laid out running `dir`. Everything that depends on either is in here.
    def build(dir_: str, max_w: float, floor: bool) -> dict:
        # a round node is as wide as its text needs and as tall as it is wide
        lines: dict[str, dict] = {}
        for s in band["states"]:
            icon_h = _ICON_H if s.get("icon") else 0
            if s.get("shape") == "diamond":
                lines[s["id"]] = diamond_lines(s["label"], s.get("sub"), max_w, icon_h, width_of, roles, env["wrap"], floor)
                continue
            l = measure_node(s["label"], s.get("sub"), max_w, width_of, roles, env["wrap"], floor, keep_words=s.get("shape") != "circle")
            if s.get("shape") == "pill":
                lines[s["id"]] = pill_lines(l, icon_h)
                continue
            if s.get("shape") != "circle":
                lines[s["id"]] = {**l, "h": l["h"] + icon_h}
                continue
            text = max([text_width(width_of, t, roles["body"], 700) for t in l["label"]] + [text_width(width_of, t, roles["note"], 400) for t in l["sub"]])
            inner = l["h"] - 16 + icon_h
            d = max(44, math.ceil((math.hypot(text, inner) + 10) / 8) * 8)  # a multiple of 8: the radius sits on the 4px grid
            lines[s["id"]] = {**l, "w": d, "h": d}
        nodes = [{"id": s["id"], "size": {"w": lines[s["id"]]["w"], "h": lines[s["id"]]["h"]}} for s in band["states"]]
        if band.get("initial"):
            nodes.insert(0, {"id": _INIT, "size": {"w": 2 * _DOT, "h": 2 * _DOT}})
        # layered layout runs on a 'right' axis; a 'down' diagram is the same layout transposed
        reserve = (_LOOP + 4 + max((label_w(t["label"]) for t in loops if t.get("label")), default=0.0)) if (dir_ == "down" and loops) else 0
        top = (_LOOP + loop_label_h + 6) if (loops and dir_ == "right") else 0

        def place_in(total: dict):
            def place(p: dict) -> dict:
                q = _swap(p) if dir_ == "down" else p
                return {"x": q["x"] + x + (w - total["w"] - reserve) / 2, "y": q["y"] + y + top}

            return place

        space = env.get("space", 1)
        layout_nodes = [{"id": n["id"], "size": swap_size(n["size"])} for n in nodes] if dir_ == "down" else nodes
        # a loop needs room beside its state (down) or between rows (right), so states do not crowd it
        gap = (GAP + _LOOP + (max((label_w(t["label"]) for t in loops if t.get("label")), default=0.0) if dir_ == "down" else 0)) if loops else js_round(GAP * space)
        level_gap = max(js_round(72 * space) if dir_ == "down" else (widest + stub_of(space) + _ARROW + 8 if widest else js_round(64 * space)), gap_for(degree, 0, space))
        layout_opts: dict = {"dir": "right", "gap": gap, "levelGap": level_gap}
        if band.get("initial"):
            layout_opts["start"] = [_INIT]
        attempt_opts: dict = {"transpose": dir_ == "down", "maxAcross": w + 0.5 - reserve, "place": place_in, "tighten": True, "round": lambda node_id: node_id in circles}
        if not (env.get("space") is None or env.get("space") == 1):
            attempt_opts["space"] = space
        if band.get("straighten") is False:
            attempt_opts["straighten"] = False
        if band.get("returns") == "outer":
            attempt_opts["returns"] = "all"
        run = layered_attempt(layout_nodes, edges, layout_opts, attempt_opts)

        def at(node_id: str) -> dict:
            p = run["lay"]["nodes"][node_id]
            return {"x": p["y"], "y": p["x"], "w": p["h"], "h": p["w"]} if dir_ == "down" else p

        return {**run, "dir": dir_, "lines": lines, "reserve": reserve, "top": top, "at": at}

    explicit_dir = band.get("dir") is not None and band.get("dir") != "auto"
    start = "down" if (band.get("dir") == "down" or (band.get("dir") is None and band.get("defaultDir") == "down")) else "right"
    plan: dict = {
        "who": words["who"], "w": w, "start": start, "keepWords": env.get("keepWords", False),
        "alt": "down" if start == "right" else "right", "explicitDir": explicit_dir,
        "mode": "auto" if band.get("dir") == "auto" else "omitted",
        "build": lambda d, mw, floor: build(d, mw, floor), "widthOf": lambda r: r["size"]["w"] + r["reserve"], "best": band.get("dir") == "auto",
    }
    if band.get("maxNodeW") is not None:
        plan["maxNodeW"] = band["maxNodeW"]
    if height_budget is not None:
        plan["heightBudget"] = height_budget
    if band.get("returns") == "outer":
        plan["notTried"] = ["returns: 'inline' (returns is written: 'outer')"]
    fitted = plan_fit(plan)
    if not fitted["ok"]:
        return {"noFit": True, "failure": fitted["failure"]}
    result, fit_applied = fitted["result"], fitted["applied"]
    dir_, lines, reserve, top, at, lay, routes, total = result["dir"], result["lines"], result["reserve"], result["top"], result["at"], result["lay"], result["routes"], result["size"]

    # a loop sits above its state when the flow runs right (room is made at the top), and to its right when the flow runs down
    # dir down: the loop and its label stick out to the right of the rightmost state (`reserve`)
    dx, dy = x + (w - total["w"] - reserve) / 2, y + top
    out: dict = {"type": "states", "x": x, "y": y, "w": w, "h": total["h"] + top, "nodes": [], "edges": [], "texts": [], "icons": [], "labels": [], "anchors": [], "labelBoxes": []}
    if band.get("flavor"):
        out["flavor"] = band["flavor"]
    if band.get("id") is not None:
        out["id"] = band["id"]
    if band.get("reveal") is not None:
        out["reveal"] = band["reveal"]
    if band.get("until") is not None:
        out["until"] = band["until"]
    if fit_applied:
        out["fitApplied"] = fit_applied

    rects: dict[str, dict] = {}
    diamonds: dict[str, dict] = {}
    for s in band["states"]:
        p = at(s["id"])
        r = {"x": p["x"] + dx, "y": p["y"] + dy, "w": p["w"], "h": p["h"]}
        rects[s["id"]] = r
        if s.get("shape") == "diamond":
            diamonds[s["id"]] = r
        node_entry: dict = {**r, "tone": s.get("tone", "plain")}
        if s.get("final"):
            node_entry["final"] = True
        if s.get("shape") == "circle":
            node_entry["circle"] = True
        if s.get("shape") in ("diamond", "pill"):
            node_entry["shape"] = s["shape"]
        out["nodes"].append(node_entry)
        out["anchors"].append({"id": s["id"], **r})
        nl = lines[s["id"]]
        text_h = len(nl["label"]) * js_round(roles["body"] * 1.4) + len(nl["sub"]) * js_round(roles["note"] * 1.4)
        # the text of a round node sits in its middle; an icon is above the text
        icon_h = _ICON_H if s.get("icon") else 0
        y0 = (r["y"] + (r["h"] - text_h - icon_h) / 2 - 8) if s.get("shape") in ("circle", "diamond") else r["y"]
        out["texts"].extend(node_runs({"x": r["x"], "y": y0 + icon_h, "w": r["w"]}, nl, roles))
        out["labelBoxes"].append({"label": s["label"], **r})
    if band.get("initial"):
        p = at(_INIT)
        out["initial"] = {"x": p["x"] + dx + _DOT, "y": p["y"] + dy + _DOT, "r": _DOT}

    # transitions: routed in the layout's own ('right') axes, then transposed for dir down and moved into the figure
    used: set[int] = set()

    def pick_transition(frm: str, to: str) -> dict | None:
        k = next((i for i, tr in enumerate(band["transitions"]) if i not in used and tr["from"] == frm and tr["to"] == to), -1)
        if k >= 0:
            used.add(k)
        return band["transitions"][k] if k >= 0 else None

    def hit(a: dict, b: dict) -> bool:
        return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]

    # a label sits on its arrow, in a chip: the middle of the arrow if free, else the nearest spot along it that clears the states and the other chips
    def add_label(own: int, text: str, pts: list[dict], const_point: dict | None = None) -> None:
        on = [] if const_point is not None else pts
        lw, lh = label_w(text), S + 8

        def box_at(c: dict) -> dict:
            return {"x": c["x"] - lw / 2, "y": c["y"] - lh / 2, "w": lw, "h": lh}

        tip = {"x": on[-1]["x"] - _ARROW, "y": on[-1]["y"] - _ARROW, "w": 2 * _ARROW, "h": 2 * _ARROW} if on else None

        def on_other(b: dict) -> bool:
            # a chip is white: on another arrow it would cut that arrow, so it keeps off every arrow but its own
            for k, e in enumerate(out["edges"]):
                if k == own:
                    continue
                pts_e = e["points"]
                for i in range(len(pts_e) - 1):
                    p, q = pts_e[i], pts_e[i + 1]
                    if hit(b, {"x": min(p["x"], q["x"]) - 1, "y": min(p["y"], q["y"]) - 1, "w": abs(p["x"] - q["x"]) + 2, "h": abs(p["y"] - q["y"]) + 2}):
                        return True
            return False

        def free(b: dict) -> bool:
            return not any(hit(b, o) for o in out["labels"]) and not any(hit(b, n) for n in out["nodes"]) and not (tip and hit(b, tip)) and not on_other(b)

        # first choice: beside the arrow's straight runs, last run first (above a horizontal one, to the right of a vertical one)
        runs: list[dict] = []
        for k in range(len(on) - 2, -1, -1):
            p, q = on[k], on[k + 1]
            last = k == len(on) - 2
            trim = _ARROW if last else 0
            if dir_ == "right" and p["y"] == q["y"]:
                ln = abs(q["x"] - p["x"]) - trim
                if ln >= lw:
                    runs.append({"x": p["x"] + _sign(q["x"] - p["x"]) * (ln / 2), "y": p["y"] - lh / 2 - 3})
            elif dir_ == "down" and p["x"] == q["x"]:
                ln = abs(q["y"] - p["y"]) - trim
                if ln >= lh + 4:
                    sgn = _sign(q["y"] - p["y"])
                    runs.append({"x": p["x"] + 6 + lw / 2, "y": p["y"] + sgn * (ln / 2)})
                    runs.append({"x": p["x"] - 6 - lw / 2, "y": p["y"] + sgn * (ln / 2)})
        # an arrow that leaves a decision (Yes / No): its chip sits at the diamond, beside the first stretch of the arrow, so it reads as the answer to that question
        from_ = diamonds.get(out["edges"][own]["from"])
        p0 = on[0] if on else None
        if from_ and p0:
            first = on[1] if len(on) > 1 else None
            if dir_ == "down" and first and first["x"] == p0["x"]:
                right = p0["x"] >= from_["x"] + from_["w"] / 2
                runs.insert(0, {"x": p0["x"] + (1 if right else -1) * (6 + lw / 2), "y": from_["y"] + from_["h"] + lh / 2 + 2})
            elif dir_ == "right" and first and first["y"] == p0["y"]:
                runs.insert(0, {"x": from_["x"] + from_["w"] + 4 + lw / 2, "y": p0["y"] + (-1 if p0["y"] < from_["y"] + from_["h"] / 2 else 1) * (lh / 2 + 3)})
        # candidates, nearest to the arrow first: its straight runs, then points along it, then spots beside those (right / left / above / below)
        offs = [(0, 0), (lw / 2 + 8, 0), (-(lw / 2 + 8), 0), (0, lh + 2), (0, -(lh + 2)), (lw / 2 + 8, lh + 2), (-(lw / 2 + 8), lh + 2), (lw / 2 + 8, -(lh + 2)), (-(lw / 2 + 8), -(lh + 2)), (0, 2 * (lh + 2)), (0, -2 * (lh + 2)), (lw + 12, 0), (-(lw + 12), 0)]
        cands: list[dict] = [{"p": p, "cost": -1.0} for p in runs]
        f = 0.05
        while f < 0.96:
            q = const_point if const_point is not None else _point_at(pts, f)
            for ox, oy in offs:
                cands.append({"p": {"x": q["x"] + ox, "y": q["y"] + oy}, "cost": math.hypot(ox, oy) + abs(f - 0.5) * 30})
            f += 0.05
        cands.sort(key=lambda c: c["cost"])
        c = next((k["p"] for k in cands if free(box_at(k["p"]))), cands[0]["p"])
        b = box_at(c)
        out["labels"].append({"text": text, **b, "tx": c["x"], "ty": b["y"] + S + 2, "size": S, "edge": own})
        out["labelBoxes"].append({"label": text, **b})

    # every arrow is routed first, then the labels are placed (a chip must know where the other arrows run)
    pending: list[dict] = []
    # the arrows that drop straight from a diamond start at its corners (one answer each) instead of at spots on its lower sides
    drops: dict[int, list[dict]] = {}
    for dia_id, dr in diamonds.items():
        idxs = [i for i, e in enumerate(lay["edges"]) if e["from"] == dia_id and e["to"] != dia_id and i in routes and e["to"] in rects]
        if not idxs:
            continue
        flip = dir_ == "right"

        def sw(p: dict, flip: bool = flip) -> dict:
            return {"x": p["y"], "y": p["x"]} if flip else p

        def sw_r(r: dict, flip: bool = flip) -> dict:
            return {"x": r["y"], "y": r["x"], "w": r["h"], "h": r["w"]} if flip else r

        original = [[sw(p) for p in routes[i]] for i in idxs]
        outs = [{"pts": original[k], "target": sw_r(rects[lay["edges"][i]["to"]])} for k, i in enumerate(idxs)]
        others = [sw_r(r) for other_id, r in rects.items() if other_id != dia_id]
        res = vertex_drops(outs, sw_r(dr), others)
        for k, i in enumerate(idxs):
            if res[k] is not original[k]:
                drops[i] = [sw(p) for p in res[k]]

    # a corner an answer leaves from is not where an arrow coming in from that side ends too: that one comes in a little above it
    # (dir 'right': the corners are the top and bottom vertices and the return comes in vertically, so it ends a little to the left of it)
    def corner_used(dia_id: str, side: str) -> bool:
        r = diamonds.get(dia_id)
        if r is None:
            return False
        lo, hi = (r["y"], r["y"] + r["h"]) if dir_ == "right" else (r["x"], r["x"] + r["w"])
        axis = "y" if dir_ == "right" else "x"
        target = lo if side == "left" else hi
        for i, p in drops.items():
            if lay["edges"][i]["from"] == dia_id and abs(p[0][axis] - target) < 1:
                return True
        return False

    for i, e in enumerate(lay["edges"]):
        t = None if e["from"] == _INIT else pick_transition(e["from"], e["to"])
        line = t["line"] if (t and t.get("line") is not None) else "solid"
        if e.get("self"):
            a = rects[e["from"]]
            cx, cy = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2
            if dir_ == "down":
                pts = [{"x": a["x"] + a["w"], "y": cy - _LOOP_W}, {"x": a["x"] + a["w"] + _LOOP, "y": cy - _LOOP_W}, {"x": a["x"] + a["w"] + _LOOP, "y": cy + _LOOP_W}, {"x": a["x"] + a["w"], "y": cy + _LOOP_W}]
                edge_entry: dict = {"from": e["from"], "to": e["to"], "points": pts, "line": line}
                if t and t.get("tone"):
                    edge_entry["tone"] = t["tone"]
                if t and t.get("strong"):
                    edge_entry["strong"] = True
                out["edges"].append(edge_entry)
                if t and t.get("label"):
                    lw = label_w(t["label"])
                    pending.append({"edge": len(out["edges"]) - 1, "text": t["label"], "pts": [], "constPoint": {"x": a["x"] + a["w"] + _LOOP + 4 + lw / 2, "y": cy}})
                continue
            pts = [{"x": cx + _LOOP_W, "y": a["y"]}, {"x": cx + _LOOP_W, "y": a["y"] - _LOOP}, {"x": cx - _LOOP_W, "y": a["y"] - _LOOP}, {"x": cx - _LOOP_W, "y": a["y"]}]
            edge_entry = {"from": e["from"], "to": e["to"], "points": pts, "line": line}
            if t and t.get("tone"):
                edge_entry["tone"] = t["tone"]
            if t and t.get("strong"):
                edge_entry["strong"] = True
            out["edges"].append(edge_entry)
            if t and t.get("label"):
                pending.append({"edge": len(out["edges"]) - 1, "text": t["label"], "pts": [], "constPoint": {"x": cx, "y": a["y"] - _LOOP - (S + 8) / 2 - 2}})
            continue
        dropped = drops.get(i)
        pts = list(dropped if dropped is not None else routes[i])
        # an end on a diamond is moved onto its outline (the arrows that share a side are spread around its middle)
        d_from, d_to = diamonds.get(e["from"]), diamonds.get(e["to"])
        if d_from and dropped is None and len(pts) > 1:
            pts[0] = onto_diamond(pts[0], pts[1], d_from)
        last, before = (pts[-1], pts[-2]) if len(pts) > 1 else (None, None)
        if d_to and last and before and len(pts) > 2 and dir_ == "down" and last["y"] == before["y"] and ((last["x"] <= d_to["x"] + 1 and corner_used(e["to"], "left")) or (last["x"] >= d_to["x"] + d_to["w"] - 1 and corner_used(e["to"], "right"))):
            up = -min(14, d_to["h"] / 4)
            pts[-1], pts[-2] = {"x": last["x"], "y": last["y"] + up}, {"x": before["x"], "y": before["y"] + up}
        elif d_to and last and before and len(pts) > 2 and dir_ == "right" and last["x"] == before["x"] and ((last["y"] <= d_to["y"] + 1 and corner_used(e["to"], "left")) or (last["y"] >= d_to["y"] + d_to["h"] - 1 and corner_used(e["to"], "right"))):
            left = -min(14, d_to["w"] / 4)
            pts[-1], pts[-2] = {"x": last["x"] + left, "y": last["y"]}, {"x": before["x"] + left, "y": before["y"]}
        if d_to and len(pts) > 1:
            pts[-1] = onto_diamond(pts[-1], pts[-2], d_to)
        edge_entry = {"from": e["from"], "to": e["to"], "points": pts, "line": line}
        if t and t.get("tone"):
            edge_entry["tone"] = t["tone"]
        if t and t.get("strong"):
            edge_entry["strong"] = True
        out["edges"].append(edge_entry)
        if t and t.get("label"):
            pending.append({"edge": len(out["edges"]) - 1, "text": t["label"], "pts": pts})
    for entry in pending:
        add_label(entry["edge"], entry["text"], entry["pts"], entry.get("constPoint"))
    return out


def render_states(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:263-312 renderStates(). NOT ported: `icons` (always empty — see
    the module docstring; the render loop over it in Node is therefore a no-op here and
    omitted)."""
    out: list[str] = []
    dim = bool(b.get("dim"))
    stroke = PALETTE["muted"] if dim else PALETTE["text"]

    def ink_of(tone: str | None) -> str:
        if dim:
            return PALETTE["muted"]
        if tone is None:
            return PALETTE["text"]
        if tone == "muted":
            return PALETTE["muted"]
        return color_of(tone, day)

    # arrowheads are drawn as shapes, not markers: a marker on a leftward end is not turned by every renderer (resvg leaves it pointing right)
    for e in b["edges"]:
        pts = list(e["points"])
        n = len(pts)
        tip, prev = pts[n - 1], pts[n - 2]
        color = ink_of(e.get("tone"))
        dx, dy = _sign(tip["x"] - prev["x"]), _sign(tip["y"] - prev["y"])
        arrow_l, arrow_w = (16, 7) if e.get("strong") else (12, 5)
        pts[n - 1] = {"x": tip["x"] - dx * (arrow_l - 2), "y": tip["y"] - dy * (arrow_l - 2)}  # the line stops inside the head
        head = f'M{snap4(tip["x"])},{snap4(tip["y"])} L{snap4(tip["x"] - dx * arrow_l - dy * arrow_w)},{snap4(tip["y"] - dy * arrow_l + dx * arrow_w)} L{snap4(tip["x"] - dx * arrow_l + dy * arrow_w)},{snap4(tip["y"] - dy * arrow_l - dx * arrow_w)} z'
        path_pts = " L".join(f"{snap4(p['x'])},{snap4(p['y'])}" for p in pts)
        out.append(f'<path d="M{path_pts}" fill="none" stroke="{color}" stroke-width="{4 if e.get("strong") else 2}"{line_attrs(None if e.get("line") == "solid" else e.get("line"))}/>\n  <path d="{head}" fill="{color}"/>')
    if b.get("initial"):
        init = b["initial"]
        out.append(f'<circle cx="{snap4(init["x"])}" cy="{snap4(init["y"])}" r="{js_num(init["r"])}" fill="{stroke}"/>')
    for n in b["nodes"]:
        if n.get("circle"):  # an event: a circle in its tone's colours
            if dim:
                fill, stroke_c = PALETTE["bg"], PALETTE["muted"]
            else:
                st = resolve_box_style(n["tone"], day)
                fill, stroke_c = st["fill"], st["stroke"]
            out.append(f'<circle cx="{snap4(n["x"] + n["w"] / 2)}" cy="{snap4(n["y"] + n["h"] / 2)}" r="{snap4(n["w"] / 2)}" fill="{fill}" stroke="{stroke_c}" stroke-width="2.5"/>')
            continue
        if n.get("shape") == "diamond":  # a decision: a diamond in its tone's colours (a path, like a gateway: a polygon does not reach the HTML output)
            st = resolve_box_style(n["tone"], day)
            fill, stroke_c, dashed = st["fill"], st["stroke"], st["dashed"]
            if dim:
                fill, stroke_c = PALETTE["bg"], PALETTE["muted"]
            rx, ry = snap4(n["x"]), snap4(n["y"])
            rw, rh = snap4(n["x"] + n["w"]) - rx, snap4(n["h"])
            dash = ' stroke-dasharray="6,4"' if dashed else (' stroke-dasharray="2,5" stroke-linecap="round"' if dim else "")
            out.append(
                f'<path d="M{js_num(rx + rw / 2)},{js_num(ry)} L{js_num(rx + rw)},{js_num(ry + rh / 2)} L{js_num(rx + rw / 2)},{js_num(ry + rh)} L{js_num(rx)},{js_num(ry + rh / 2)} Z" '
                f'fill="{fill}" stroke="{stroke_c}" stroke-width="2.5" stroke-linejoin="round"{dash}/>'
            )
            continue
        if n.get("shape") == "pill":  # a terminator: the box's rect with the ends rounded to half the height
            rect_svg = render_box_rect(x=n["x"], y=n["y"], w=n["w"], h=n["h"], tone=n["tone"], dim=dim, day=day, default_tone="plain")
            out.append(rect_svg.replace('rx="8"', f'rx="{js_num(snap4(n["h"]) / 2)}"', 1))
            continue
        out.append(render_box_rect(x=n["x"], y=n["y"], w=n["w"], h=n["h"], tone=n["tone"], dim=dim, day=day, default_tone="plain"))
        # the inner outline of an end state: on a solid fill its stroke would be the fill colour, so it is drawn in the text colour (white)
        inner = render_box_rect(x=n["x"] + 4, y=n["y"] + 4, w=n["w"] - 8, h=n["h"] - 8, tone=n["tone"], dim=dim, day=day, default_tone="plain").replace('rx="8"', 'rx="5"', 1)
        if n.get("final"):
            if not dim and is_solid_tone(n["tone"]):
                color = color_of(tone_style(n["tone"]).text, day)
                inner = re.sub(r'stroke="[^"]*"', f'stroke="{color}"', inner, count=1)
            out.append(inner)

    def text_ink(t: dict) -> str:
        if dim:
            return PALETTE["muted"]
        n = next((r for r in b["nodes"] if t["x"] >= r["x"] and t["x"] <= r["x"] + r["w"] and t["y"] > r["y"] and t["y"] <= r["y"] + r["h"]), None)
        if n and is_solid_tone(n["tone"]):
            return color_of(tone_style(n["tone"]).text, day)  # white on the fill, the sub line too
        if t.get("muted"):
            return PALETTE["text"] if (n and tone_style(n["tone"]).fill == "soft") else PALETTE["muted"]  # muted on a soft fill is 4.48:1, under 4.5
        return color_of(tone_style(n["tone"] if n else None).text, day)

    for t in b["texts"]:
        bold = ' font-weight="700"' if t["bold"] else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}" text-anchor="middle" font-size="{t["size"]}"{bold} fill="{text_ink(t)}">{emoji_span(t["text"])}</text>')
    for l in b["labels"]:
        out.append(f'<rect x="{snap4(l["x"])}" y="{snap4(l["y"])}" width="{snap4(l["w"])}" height="{js_num(l["h"])}" fill="{PALETTE["bg"]}"/>')
        out.append(f'<text x="{js_round(l["tx"])}" y="{js_round(l["ty"] + snap4(l["y"]) - l["y"])}" text-anchor="middle" font-size="{l["size"]}" fill="{stroke}">{emoji_span(l["text"])}</text>')
    return "\n  ".join(out)
