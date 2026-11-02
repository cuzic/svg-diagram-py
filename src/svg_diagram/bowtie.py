"""1:1 port of lib/bowtie.ts's layoutBowtie() (exported, golden-tested live) and
lib/emit-bowtie.ts's renderBowtie(). bowtie(): threats on the left, each through its
preventive barriers, into the top event in the middle (under its hazard); out through the
mitigating barriers to the consequences on the right. A fixed layout: no tree or layered
routing — the ONLY auto-layout dependency is the width-narrowing cascade
(lib/fit-width.ts's fitLayout()), ported in scope in fit_width.py (shared with fta.py).

Golden master: lib/bowtie.ts + lib/emit-bowtie.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .emit_boxes import render_box_rect
from .emit_common import arrow_path, emoji_span, js_round, snap4
from .fit_width import fit_layout
from .tokens import PALETTE, color_of, tone_style
from .tree_text import measure_node, node_runs

COL_GAP, BUS_GAP, ROW_GAP, KNOT_R, STEM, TOP_MIN_W, TOP_MAX_LINES = 32, 56, 20, 14, 14, 150, 3


def _blank(s: object) -> bool:
    return not isinstance(s, str) or not s.strip()


def bowtie_check(data: dict) -> None:
    """lib/bowtie.ts:17-29 bowtieCheck()."""
    if not isinstance(data, dict):
        raise ValueError("bowtie({top, threats, consequences}) needs the top event and the sides")
    if _blank(data.get("top")):
        raise ValueError("bowtie(): top is the text of the top event (the loss of control)")
    if data.get("hazard") is not None and _blank(data["hazard"]):
        raise ValueError("bowtie(): hazard is text (what is controlled), or leave it out")
    for key in ("threats", "consequences"):
        lst = data.get(key)
        if not isinstance(lst, list) or len(lst) == 0:
            raise ValueError(f"bowtie(): {key} needs at least one entry")
        for i, s in enumerate(lst):
            if not s or _blank(s.get("label")):
                raise ValueError(f"bowtie(): {key} {i + 1} needs a label")
            barriers = s.get("barriers")
            if barriers is not None and not isinstance(barriers, list):
                raise ValueError(f'bowtie(): "{s.get("label")}": barriers is a list of texts')
            for j, b in enumerate(barriers or []):
                if _blank(b):
                    raise ValueError(f'bowtie(): "{s.get("label")}": barrier {j + 1} needs text')


def bowtie_band(data: dict, *, max_node_w: float | str | None = None, id: str | None = None) -> dict:
    """lib/dsl/diagrams.ts:314-318 bowtie() (the band-construction half; this port has no
    separate bowtieBand() export to mirror — Node builds it inline in the DSL function)."""
    bowtie_check(data)
    if max_node_w is not None and max_node_w != "auto" and not (isinstance(max_node_w, (int, float)) and max_node_w >= 80):
        raise ValueError(f"bowtie(): maxNodeW must be a number >= 80 or 'auto' (got {max_node_w!r})")

    def side(s: dict) -> dict:
        out = {"label": s["label"]}
        if s.get("barriers") is not None:
            out["barriers"] = list(s["barriers"])
        return out

    band = {"type": "bowtie", "event": data["top"], "threats": [side(s) for s in data["threats"]], "consequences": [side(s) for s in data["consequences"]]}
    if data.get("hazard") is not None:
        band["hazard"] = data["hazard"]
    if max_node_w is not None:
        band["maxNodeW"] = max_node_w
    if id is not None:
        band["id"] = id
    return band


def _col_widths(rows: list[list[dict]]) -> list[float]:
    n = max((len(r) for r in rows), default=0)
    return [max((r[k]["lines"]["w"] if k < len(r) else 0) for r in rows) for k in range(n)]


def _place(band: dict, max_w: float, width_of, roles: dict, mode: str, floor: bool) -> dict:
    """lib/bowtie.ts:80-142 place()."""

    def measure(label: str, role: str, cap: float = max_w) -> dict:
        return {"role": role, "label": label, "lines": measure_node(label, None, cap, width_of, roles, mode, floor)}

    left = [[measure(t["label"], "threat"), *(measure(b, "barrier") for b in t.get("barriers") or [])] for t in band["threats"]]
    right = [{"barriers": [measure(b, "barrier") for b in c.get("barriers") or []], "end": measure(c["label"], "consequence")} for c in band["consequences"]]
    wide = max(max_w, TOP_MIN_W + 40)
    top = measure(band["event"], "event", wide)
    if len(top["lines"]["label"]) > TOP_MAX_LINES:
        raise ValueError(f'bowtie(): the top event "{band["event"]}" takes more than {TOP_MAX_LINES} lines; shorten it')
    hazard = measure(band["hazard"], "hazard", wide) if band.get("hazard") else None
    top_w = max(TOP_MIN_W, top["lines"]["w"], hazard["lines"]["w"] if hazard else 0)
    lw = _col_widths(left)
    rw = _col_widths([r["barriers"] for r in right])
    end_w = max(r["end"]["lines"]["w"] for r in right)
    left_w = sum(lw) + COL_GAP * (len(lw) - 1)
    right_w = sum(rb + COL_GAP for rb in rw) + end_w
    total_w = left_w + BUS_GAP + top_w + BUS_GAP + right_w

    def row_h(items: list[dict]) -> float:
        return max(i["lines"]["h"] for i in items)

    row_h_l = max(row_h(r) for r in left)
    row_h_r = max(row_h([*r["barriers"], r["end"]]) for r in right)
    stack_h = (hazard["lines"]["h"] + STEM if hazard else 0) + 2 * KNOT_R + STEM + top["lines"]["h"]

    def side_h(n: int, h: float) -> float:
        return n * h + (n - 1) * ROW_GAP

    big_h = max(side_h(len(left), row_h_l), side_h(len(right), row_h_r), stack_h)

    def centre(i: int, n: int, h: float) -> float:
        return h / 2 + i * (big_h - h) / (n - 1) if n > 1 else big_h / 2

    nodes: list[dict] = []
    edges: list[dict] = []
    top_x = left_w + BUS_GAP
    cy0 = (big_h - stack_h) / 2
    if hazard:
        nodes.append({"x": top_x + (top_w - hazard["lines"]["w"]) / 2, "y": cy0, "w": hazard["lines"]["w"], "h": hazard["lines"]["h"], "role": "hazard", "label": hazard["label"], "lines": hazard["lines"]})
        cy0 += hazard["lines"]["h"] + STEM
    knot = {"cx": top_x + top_w / 2, "cy": cy0 + KNOT_R}
    cy0 += 2 * KNOT_R + STEM
    top_rect = {"x": top_x, "y": cy0, "w": top_w, "h": top["lines"]["h"], "role": "event", "label": top["label"], "lines": top["lines"]}
    nodes.append(top_rect)

    def entry(cy: float) -> float:
        return min(max(cy, top_rect["y"] + 10), top_rect["y"] + top_rect["h"] - 10)

    if hazard:
        edges.append({"points": [{"x": knot["cx"], "y": nodes[0]["y"] + nodes[0]["h"]}, {"x": knot["cx"], "y": knot["cy"] - KNOT_R}], "arrow": False})
    edges.append({"points": [{"x": knot["cx"], "y": knot["cy"] + KNOT_R}, {"x": knot["cx"], "y": top_rect["y"]}], "arrow": False})

    def dedupe(pts: list[dict]) -> list[dict]:
        out = []
        for j, q in enumerate(pts):
            if j == 0 or q["x"] != pts[j - 1]["x"] or q["y"] != pts[j - 1]["y"]:
                out.append(q)
        return out

    bus_l, bus_r = left_w + BUS_GAP / 2, top_x + top_w + BUS_GAP / 2
    for i, row in enumerate(left):
        cy = centre(i, len(left), row_h_l)
        px, prev = 0, None
        for k, it in enumerate(row):
            p = {"x": px, "y": cy - it["lines"]["h"] / 2, "w": lw[k], "h": it["lines"]["h"], "role": it["role"], "label": it["label"], "lines": it["lines"]}
            nodes.append(p)
            if prev:
                edges.append({"points": [{"x": prev["x"] + prev["w"], "y": cy}, {"x": p["x"], "y": cy}], "arrow": True})
            prev = p
            px += lw[k] + COL_GAP
        end, ye = prev, entry(cy)
        edges.append({"points": dedupe([{"x": end["x"] + end["w"], "y": cy}, {"x": bus_l, "y": cy}, {"x": bus_l, "y": ye}, {"x": top_x, "y": ye}]), "arrow": True})
    for i, row in enumerate(right):
        cy = centre(i, len(right), row_h_r)
        px, prev = top_x + top_w + BUS_GAP, None

        def put(it: dict, pw: float, px_: float) -> dict:
            p = {"x": px_, "y": cy - it["lines"]["h"] / 2, "w": pw, "h": it["lines"]["h"], "role": it["role"], "label": it["label"], "lines": it["lines"]}
            nodes.append(p)
            if prev:
                edges.append({"points": [{"x": prev["x"] + prev["w"], "y": cy}, {"x": p["x"], "y": cy}], "arrow": True})
            else:
                ye = entry(cy)
                edges.append({"points": dedupe([{"x": top_x + top_w, "y": ye}, {"x": bus_r, "y": ye}, {"x": bus_r, "y": cy}, {"x": p["x"], "y": cy}]), "arrow": True})
            return p

        for k, it in enumerate(row["barriers"]):
            prev = put(it, rw[k], px)
            px += rw[k] + COL_GAP
        put(row["end"], end_w, total_w - end_w)
    return {"w": total_w, "h": big_h, "nodes": nodes, "edges": edges, "knot": knot}


def layout_bowtie(band: dict, x: float, y: float, w: float, width_of, roles: dict, mode: str) -> dict:
    """lib/bowtie.ts:44-76 layoutBowtie()."""
    bowtie_check({"hazard": band.get("hazard"), "top": band["event"], "threats": band["threats"], "consequences": band["consequences"]})

    def attempt(max_w: float, floor: bool) -> dict:
        g = _place(band, max_w, width_of, roles, mode, floor)
        return {"size": {"w": g["w"], "h": g["h"]}, "score": {"crossings": 0, "bends": 0}, "maxW": max_w}

    auto = band.get("maxNodeW") == "auto"
    written = band["maxNodeW"] if isinstance(band.get("maxNodeW"), (int, float)) else None
    fitted = fit_layout(
        who="bowtie()", w=w, max_node_w=written, mode="auto" if auto else "omitted",
        build=lambda max_w, floor: attempt(max_w, floor),
        fix="a wider figure (diagram({width})), fewer barriers in a row, or shorter texts",
    )
    g = _place(band, fitted["result"]["maxW"], width_of, roles, mode, False)
    dx, dy = x + (w - g["w"]) / 2, y
    out: dict = {
        "type": "bowtie", "x": x, "y": y, "w": w, "h": g["h"],
        "nodes": [{"x": n["x"] + dx, "y": n["y"] + dy, "w": n["w"], "h": n["h"], "role": n["role"]} for n in g["nodes"]],
        "edges": [{"arrow": e["arrow"], "points": [{"x": p["x"] + dx, "y": p["y"] + dy} for p in e["points"]]} for e in g["edges"]],
        "knot": {"cx": g["knot"]["cx"] + dx, "cy": g["knot"]["cy"] + dy, "r": KNOT_R},
        "texts": [], "anchors": [], "labelBoxes": [],
    }
    if band.get("id") is not None:
        out["id"] = band["id"]
    if band.get("reveal") is not None:
        out["reveal"] = band["reveal"]
    if band.get("until") is not None:
        out["until"] = band["until"]
    if fitted["applied"]:
        out["fitApplied"] = fitted["applied"]
    for i, n in enumerate(g["nodes"]):
        r = out["nodes"][i]
        out["labelBoxes"].append({"label": n["label"], "x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]})
        out["texts"].extend(node_runs(r, n["lines"], roles))
    return out


_ROLE_TONE = {"hazard": "muted", "threat": "changed", "barrier": "accent", "event": "danger", "consequence": "danger"}


def render_bowtie(b: dict, day: int | str = 1) -> str:
    """lib/emit-bowtie.ts:12-26 renderBowtie()."""
    out = []
    dim = bool(b.get("dim"))
    line_color = PALETTE["muted"] if dim else PALETTE["text"]
    for e in b["edges"]:
        if e["arrow"]:
            out.append(arrow_path(e["points"], line_color, None))
        else:
            pts = " L".join(f"{snap4(p['x'])},{snap4(p['y'])}" for p in e["points"])
            out.append(f'<path d="M{pts}" fill="none" stroke="{line_color}" stroke-width="2"/>')
    knot = b["knot"]
    knot_stroke = PALETTE["muted"] if dim else PALETTE["danger"]
    out.append(f'<circle cx="{snap4(knot["cx"])}" cy="{snap4(knot["cy"])}" r="{knot["r"]}" fill="{PALETTE["bg"]}" stroke="{knot_stroke}" stroke-width="3"/>')
    for n in b["nodes"]:
        out.append(render_box_rect(x=n["x"], y=n["y"], w=n["w"], h=n["h"], tone=_ROLE_TONE[n["role"]], dim=dim, day=day, default_tone="plain"))
    for t in b["texts"]:
        fill = PALETTE["muted"] if dim else (PALETTE["muted"] if t["muted"] else color_of(tone_style("plain").text, day))
        weight = ' font-weight="700"' if t["bold"] else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}" text-anchor="middle" font-size="{t["size"]}"{weight} fill="{fill}">{emoji_span(t["text"])}</text>')
    return "\n  ".join(out)
