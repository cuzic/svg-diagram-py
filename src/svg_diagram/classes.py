"""1:1 port of lib/classes.ts's layoutClassesBand() (exported, golden-tested live) and
lib/emit-figures.ts's renderClasses(): UML classes (name / attributes / methods
compartments) and the relations between them, placed in layers (layered_route.py's
layered_attempt(), on top of graph_layout.py's layout_layered() — see BANDS.md's Tier 3
note, now resolved as reusable infra) so a parent sits above its children. Relations are
orthogonal arrows with the UML end marks: hollow triangle (inherit/implement), diamond on
the whole (compose/aggregate), open arrow (arrow/depend).

Depends on fit_width.py's fit_layout()/plan_fit() (the general direction+width search
engine, also newly ported) for the dir 'down'/'right' exploration.

NOT ported: classesTexts() (a pre-registration list for Node's real text measurement, same
reason fta.py's ftaTexts()/bpmn.py's bpmnTexts() are not ported — this port measures
synchronously via width_of).

Golden master: lib/classes.ts + lib/emit-figures.ts's renderClasses() (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
from collections.abc import Callable

from .atoms import text_width
from .emit_boxes import render_box_rect
from .emit_common import _sign, emoji_span, js_num, js_round, snap4
from .fit_width import fit_layout
from .layered_route import gap_for, layered_attempt
from .tokens import PALETTE, color_of, resolve_box_style, tone_style
from .tree_text import line_h

PAD_X, PAD_Y, MIN_W, GAP, LEVEL_GAP, LOOP, CHIP_PAD = 12, 6, 110, 36, 72, 26, 5
RELATION_KINDS = ["assoc", "arrow", "inherit", "implement", "compose", "aggregate", "depend"]


def classes_band(
    classes: list[dict], relations: list[dict], *, dir: str | None = None, straighten: bool | None = None, id: str | None = None, reveal: float | None = None, until: float | None = None
) -> dict:
    """lib/dsl/diagrams.ts:92-100 classDiagram()."""
    if not classes:
        raise ValueError("classDiagram(classes, relations) needs at least one class")
    if dir is not None and dir not in ("down", "right", "auto"):
        raise ValueError(f"classDiagram(): dir must be 'down', 'right' or 'auto' (got {dir})")
    band: dict = {"type": "classes", "classes": list(classes), "relations": list(relations)}
    if dir is not None:
        band["dir"] = dir
    if straighten is not None:
        band["straighten"] = straighten
    if id is not None:
        band["id"] = id
    if reveal is not None:
        band["reveal"] = reveal
    if until is not None:
        band["until"] = until
    return band


def _flip(k: str | None) -> bool:
    return k in ("inherit", "implement")


def layout_classes_band(band: dict, x: float, y: float, w: float, width_of, roles: dict, env: dict, height_budget: float | None = None) -> dict:
    """lib/classes.ts:27-150 layoutClassesBand()."""
    B, S = roles["body"], roles["note"]
    ids: set[str] = set()
    for c in band["classes"]:
        if not isinstance(c.get("id"), str) or not c["id"]:
            raise ValueError("classDiagram(): every class needs an id")
        if c["id"] in ids:
            raise ValueError(f'classDiagram(): duplicate class id "{c["id"]}"')
        ids.add(c["id"])
    for r in band["relations"]:
        for e in (r["from"], r["to"]):
            if e not in ids:
                raise ValueError(f'classDiagram(): relation {r["from"]} -> {r["to"]} names unknown class "{e}"')
        if r.get("kind") is not None and r["kind"] not in RELATION_KINDS:
            raise ValueError(f'classDiagram(): relation {r["from"]} -> {r["to"]} has kind {r["kind"]} (use {" | ".join(RELATION_KINDS)})')

    # measure each class: header (stereotype, name), attributes, methods
    meas: dict[str, dict] = {}
    for c in band["classes"]:
        head: list[dict] = []
        st = c.get("stereotype") or ("abstract" if c.get("abstract") else None)
        if st:
            head.append({"text": f"«{st}»", "bold": False, "size": S})
        head.append({"text": c.get("name") or c["id"], "bold": True, "size": B})
        attrs, methods = c.get("attrs") or [], c.get("methods") or []
        tw = max(
            [text_width(width_of, l["text"], l["size"], 700 if l["bold"] else 400) for l in head] + [text_width(width_of, l, B, 400) for l in (*attrs, *methods)]
        )
        head_h = 2 * PAD_Y + sum(line_h(l["size"]) for l in head)
        attrs_h = (2 * PAD_Y + len(attrs) * line_h(B)) if attrs else 0
        methods_h = (2 * PAD_Y + len(methods) * line_h(B)) if methods else 0
        meas[c["id"]] = {"head": head, "attrs": attrs, "methods": methods, "w": max(MIN_W, math.ceil(tw + 2 * PAD_X)), "h": head_h + attrs_h + methods_h, "headH": head_h, "attrsH": attrs_h}

    def label_w(t: str) -> float:
        return math.ceil(text_width(width_of, t, S, 400)) + 2 * CHIP_PAD

    # inheritance and implementation put the parent first (on top); the drawn arrow still runs child -> parent
    edges = [({"from": r["to"], "to": r["from"]} if _flip(r.get("kind")) else {"from": r["from"], "to": r["to"]}) for r in band["relations"]]
    widest_label = max([label_w(r["label"]) for r in band["relations"] if r.get("label")], default=0.0)
    degree = max(
        [1.0, *(max(sum(1 for r in band["relations"] if r["from"] == c["id"] and r["from"] != r["to"]), sum(1 for r in band["relations"] if r["to"] == c["id"] and r["from"] != r["to"])) for c in band["classes"])]
    )

    def swap(p: dict) -> dict:
        return {"x": p["y"], "y": p["x"]}

    has_loop = any(r["from"] == r["to"] for r in band["relations"])
    loop_label_w = max([label_w(r["label"]) for r in band["relations"] if r["from"] == r["to"] and r.get("label")], default=0.0)
    space = env.get("space", 1)

    # One whole attempt: the layout running `dir`. Everything that depends on it is in here.
    def build(dir_: str) -> dict:
        nodes = []
        for c in band["classes"]:
            m = meas[c["id"]]
            nodes.append({"id": c["id"], "size": ({"w": m["h"], "h": m["w"]} if dir_ == "down" else {"w": m["w"], "h": m["h"]})})
        loop_rows = (LOOP + S + 8 + 4) if (dir_ == "right" and has_loop) else 0  # a loop above a class (dir right) needs room above it, between rows too
        # a loop sits to the right of its class when the flow runs down (its arrows leave through the bottom), above it when the flow runs right
        reserve = (LOOP + 8 + max(loop_label_w, 40)) if (has_loop and dir_ == "down") else 0
        top = (LOOP + S + 8 + 8) if (has_loop and dir_ == "right") else 0

        def place_in(size: dict) -> Callable[[dict], dict]:
            def place(p: dict) -> dict:
                q = swap(p) if dir_ == "down" else p
                return {"x": q["x"] + x + (w - size["w"] - reserve) / 2, "y": q["y"] + y + top}

            return place

        level_gap = max(js_round((LEVEL_GAP + 16 if dir_ == "down" else LEVEL_GAP) * space), gap_for(degree, widest_label if dir_ == "right" else 0))
        attempt_opts: dict = {"portStep": 22, "transpose": dir_ == "down", "maxAcross": w + 0.5 - reserve, "place": place_in, "tighten": True}
        if band.get("straighten") is False:
            attempt_opts["straighten"] = False
        # wide steps: two hollow triangles on one side do not touch
        run = layered_attempt(nodes, edges, {"dir": "right", "gap": GAP + loop_rows, "levelGap": level_gap}, attempt_opts)
        return {**run, "dir": dir_, "reserve": reserve, "top": top}

    explicit_dir = band.get("dir") is not None and band.get("dir") != "auto"
    start = "right" if band.get("dir") == "right" else "down"
    plan: dict = {
        "who": "classDiagram()", "w": w, "start": start, "keepWords": env.get("keepWords", False),
        "alt": "right" if start == "down" else "down", "explicitDir": explicit_dir,
        "mode": "auto" if band.get("dir") == "auto" else "omitted", "narrow": False,
        "build": lambda d, _mw, _floor: build(d), "widthOf": lambda r: r["size"]["w"] + r["reserve"], "best": band.get("dir") == "auto",
    }
    if height_budget is not None:
        plan["heightBudget"] = height_budget
    fitted = fit_layout(plan)
    result, fit_applied = fitted["result"], fitted["applied"]
    dir_, reserve, top, lay, routes, total = result["dir"], result["reserve"], result["top"], result["lay"], result["routes"], result["size"]

    dx, dy = x + (w - total["w"] - reserve) / 2, y + top
    out: dict = {"type": "classes", "x": x, "y": y, "w": w, "h": total["h"] + top, "nodes": [], "edges": [], "texts": [], "labels": [], "anchors": [], "labelBoxes": []}
    if band.get("id") is not None:
        out["id"] = band["id"]
    if band.get("reveal") is not None:
        out["reveal"] = band["reveal"]
    if band.get("until") is not None:
        out["until"] = band["until"]
    if fit_applied:
        out["fitApplied"] = fit_applied

    rects: dict[str, dict] = {}
    for c in band["classes"]:
        p, m = lay["nodes"][c["id"]], meas[c["id"]]
        r = {"x": p["y"] + dx, "y": p["x"] + dy, "w": m["w"], "h": m["h"]} if dir_ == "down" else {"x": p["x"] + dx, "y": p["y"] + dy, "w": m["w"], "h": m["h"]}
        rects[c["id"]] = r
        dividers: list[float] = []
        if m["attrs"] or m["methods"]:
            dividers.append(r["y"] + m["headH"])
        if m["attrs"] and m["methods"]:
            dividers.append(r["y"] + m["headH"] + m["attrsH"])
        out["nodes"].append({**r, "tone": c.get("tone", "plain"), "dividers": dividers})
        out["anchors"].append({"id": c["id"], **r})
        out["labelBoxes"].append({"label": c.get("name") or c["id"], **r})
        ty = r["y"] + PAD_Y
        for l in m["head"]:
            out["texts"].append({"text": l["text"], "x": r["x"] + r["w"] / 2, "y": ty + l["size"], "size": l["size"], "bold": l["bold"], "muted": not l["bold"], "anchor": "middle"})
            ty += line_h(l["size"])
        ty = r["y"] + m["headH"] + PAD_Y
        for l in [*m["attrs"], *m["methods"]]:
            if m["methods"] and l == m["methods"][0] and m["attrs"]:
                ty = r["y"] + m["headH"] + m["attrsH"] + PAD_Y
            out["texts"].append({"text": l, "x": r["x"] + PAD_X, "y": ty + B, "size": B, "bold": False, "muted": False, "anchor": "start"})
            ty += line_h(B)

    def hit(a: dict, b: dict) -> bool:
        return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]

    def at_t(pts: list[dict], t: float) -> dict:
        """A point `t` (0-1) of the way along a polyline (by length)."""
        lens = [abs(pts[i + 1]["x"] - pts[i]["x"]) + abs(pts[i + 1]["y"] - pts[i]["y"]) for i in range(len(pts) - 1)]
        d = sum(lens) * t
        for i, ln in enumerate(lens):
            if d <= ln or i == len(lens) - 1:
                f = d / ln if ln else 0
                return {"x": pts[i]["x"] + (pts[i + 1]["x"] - pts[i]["x"]) * f, "y": pts[i]["y"] + (pts[i + 1]["y"] - pts[i]["y"]) * f}
            d -= ln
        return pts[0]

    def chip(own: int, text: str, cands: list[dict]) -> None:
        lw, lh = label_w(text), S + 8

        def box(c: dict) -> dict:
            return {"x": c["x"] - lw / 2, "y": c["y"] - lh / 2, "w": lw, "h": lh}

        def on_other(b: dict) -> bool:
            # a chip is white: on another relation it would cut that line, so it keeps off every line but its own
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
            return not any(hit(b, o) for o in out["labels"]) and not any(hit(b, n) for n in out["nodes"]) and not on_other(b)

        c = next((p for p in cands if free(box(p))), cands[0])
        b = box(c)
        out["labels"].append({"text": text, **b, "tx": c["x"], "ty": b["y"] + S + 2, "size": S, "edge": own})
        out["labelBoxes"].append({"label": text, **b})

    def near(pts: list[dict], end: int, along: float, side: float) -> dict:
        """A point `along` px from the end of a polyline (end 0: the start) and `side` px to
        its left of the direction of travel."""
        p = pts[0] if end == 0 else pts[-1]
        q = pts[1] if end == 0 else pts[-2]
        ux, uy = _sign(q["x"] - p["x"]), _sign(q["y"] - p["y"])
        return {"x": p["x"] + ux * along - uy * side, "y": p["y"] + uy * along + ux * side}

    pending: list[tuple[int, str, list[dict]]] = []
    for i, e in enumerate(lay["edges"]):
        r = band["relations"][e["index"]]
        kind = r.get("kind", "assoc")
        line = "dashed" if kind in ("implement", "depend") else "solid"
        if e.get("self"):
            a = rects[r["from"]]
            cy, cx = a["y"] + a["h"] / 2, a["x"] + a["w"] / 2
            lh = S + 8
            if dir_ == "right":  # above the class: out of the top to the right of the middle, back in to the left of it
                pts = [{"x": cx + 12, "y": a["y"]}, {"x": cx + 12, "y": a["y"] - LOOP}, {"x": cx - 12, "y": a["y"] - LOOP}, {"x": cx - 12, "y": a["y"]}]
                out["edges"].append({"from": r["from"], "to": r["to"], "kind": kind, "line": line, "points": pts})
                own = len(out["edges"]) - 1
                if r.get("label"):
                    pending.append((own, r["label"], [{"x": cx, "y": a["y"] - LOOP - lh / 2 - 2}]))
                if r.get("fromMult"):
                    pending.append((own, r["fromMult"], [{"x": cx + 12 + 4 + label_w(r["fromMult"]) / 2, "y": a["y"] - LOOP / 2}]))
                if r.get("toMult"):
                    pending.append((own, r["toMult"], [{"x": cx - 12 - 4 - label_w(r["toMult"]) / 2, "y": a["y"] - LOOP / 2}]))
                continue
            pts = [{"x": a["x"] + a["w"], "y": cy - 10}, {"x": a["x"] + a["w"] + LOOP, "y": cy - 10}, {"x": a["x"] + a["w"] + LOOP, "y": cy + 10}, {"x": a["x"] + a["w"], "y": cy + 10}]
            out["edges"].append({"from": r["from"], "to": r["to"], "kind": kind, "line": line, "points": pts})
            own = len(out["edges"]) - 1
            if r.get("label"):
                pending.append((own, r["label"], [{"x": a["x"] + a["w"] + LOOP + 4 + label_w(r["label"]) / 2, "y": cy}]))
            # the multiplicities sit above and below the little loop, at its two ends
            lx = a["x"] + a["w"] + LOOP / 2 + 6
            if r.get("fromMult"):
                pending.append((own, r["fromMult"], [{"x": lx, "y": cy - 10 - lh / 2 - 3}, {"x": lx + 14, "y": cy - 10 - lh / 2 - 3}]))
            if r.get("toMult"):
                pending.append((own, r["toMult"], [{"x": lx, "y": cy + 10 + lh / 2 + 3}, {"x": lx + 14, "y": cy + 10 + lh / 2 + 3}]))
            continue
        raw = routes[i]
        pts = list(reversed(raw)) if _flip(r.get("kind")) else raw  # drawn from the child to the parent
        out["edges"].append({"from": r["from"], "to": r["to"], "kind": kind, "line": line, "points": pts})
        own = len(out["edges"]) - 1
        if r.get("fromMult"):
            pending.append((own, r["fromMult"], [near(pts, 0, 28, 12), near(pts, 0, 28, -12), near(pts, 0, 40, 12), near(pts, 0, 40, -12)]))
        if r.get("toMult"):
            pending.append((own, r["toMult"], [near(pts, 1, 22, 12), near(pts, 1, 22, -12), near(pts, 1, 34, 12), near(pts, 1, 34, -12)]))
        if r.get("label"):
            lw = label_w(r["label"])
            along_pts = [at_t(pts, t) for t in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8)]
            offsets = [(lw / 2 + 8, 0), (-(lw / 2 + 8), 0), (0, -22), (0, 22), (lw / 2 + 8, 22), (-(lw / 2 + 8), 22), (lw / 2 + 8, -22), (-(lw / 2 + 8), -22), (0, 44), (0, -44)]
            # on the line first; else beside it (a vertical run takes the chip to its side, a horizontal one above or below), nearest first
            extra = [{"x": p["x"] + ox, "y": p["y"] + oy} for ox, oy in offsets for p in along_pts]
            pending.append((own, r["label"], [*along_pts, *extra]))
    for own, text, cands in pending:  # every relation is routed first: a chip must know where the other lines run
        chip(own, text, cands)
    return out


def render_classes(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:410-441 renderClasses()."""
    out: list[str] = []
    dim = bool(b.get("dim"))
    ink = PALETTE["muted"] if dim else PALETTE["text"]
    bg = PALETTE["bg"]
    for e in b["edges"]:
        pts = e["points"]
        first, second, tip, prev = pts[0], pts[1], pts[-1], pts[-2]
        path_pts = " L".join(f"{snap4(p['x'])},{snap4(p['y'])}" for p in pts)
        dash = ' stroke-dasharray="6,4"' if e["line"] == "dashed" else ""
        out.append(f'<path d="M{path_pts}" fill="none" stroke="{ink}" stroke-width="2"{dash}/>')

        def at_mark(p: dict, q: dict, length: float, width: float, shape: str, fill: str) -> str:
            # the mark sits at p, pointing away from q (its body runs back toward q)
            dx, dy = _sign(p["x"] - q["x"]), _sign(p["y"] - q["y"])

            def f(a: float, c: float) -> str:
                return f"{snap4(p['x'] - dx * a - dy * c)},{snap4(p['y'] - dy * a + dx * c)}"

            if shape == "open":
                return f'<path d="M{f(length, width)} L{snap4(p["x"])},{snap4(p["y"])} L{f(length, -width)}" fill="none" stroke="{ink}" stroke-width="2"/>'
            la = length if shape == "tri" else length / 2
            mid = f"L{f(length, 0)} " if shape == "dia" else ""
            return f'<path d="M{snap4(p["x"])},{snap4(p["y"])} L{f(la, width)} {mid}L{f(la, -width)} z" fill="{fill}" stroke="{ink}" stroke-width="2"/>'

        kind = e.get("kind")
        if kind in ("inherit", "implement"):
            out.append(at_mark(tip, prev, 14, 8, "tri", bg))
        elif kind in ("arrow", "depend"):
            out.append(at_mark(tip, prev, 12, 6, "open", bg))
        elif kind == "compose":
            out.append(at_mark(first, second, 20, 7, "dia", ink))
        elif kind == "aggregate":
            out.append(at_mark(first, second, 20, 7, "dia", bg))
    for nd in b["nodes"]:
        out.append(render_box_rect(x=nd["x"], y=nd["y"], w=nd["w"], h=nd["h"], tone=nd["tone"], dim=dim, day=day, default_tone="plain"))
        for yv in nd["dividers"]:
            stroke = PALETTE["muted"] if dim else resolve_box_style(nd["tone"], day)["stroke"]
            out.append(f'<path d="M{snap4(nd["x"])},{snap4(yv)} H{snap4(nd["x"] + nd["w"])}" fill="none" stroke="{stroke}" stroke-width="2"/>')
    for t in b["texts"]:
        n = next((r for r in b["nodes"] if t["x"] >= r["x"] and t["x"] <= r["x"] + r["w"] and t["y"] > r["y"] and t["y"] <= r["y"] + r["h"]), None)
        anchor = ' text-anchor="middle"' if t["anchor"] == "middle" else ""
        bold = ' font-weight="700"' if t["bold"] else ""
        if dim:
            color = PALETTE["muted"]
        elif t["muted"]:
            color = PALETTE["text"] if (n and tone_style(n["tone"]).fill == "soft") else PALETTE["muted"]
        else:
            color = color_of(tone_style(n["tone"] if n else None).text, day)
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}"{anchor} font-size="{t["size"]}"{bold} fill="{color}">{emoji_span(t["text"])}</text>')
    for l in b["labels"]:
        out.append(f'<rect x="{snap4(l["x"])}" y="{snap4(l["y"])}" width="{snap4(l["w"])}" height="{js_num(l["h"])}" fill="{bg}"/>')
        out.append(f'<text x="{js_round(l["tx"])}" y="{js_round(l["ty"] + snap4(l["y"]) - l["y"])}" text-anchor="middle" font-size="{l["size"]}" fill="{ink}">{emoji_span(l["text"])}</text>')
    return "\n  ".join(out)
