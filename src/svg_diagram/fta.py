"""1:1 port of lib/fta.ts's layoutFta() (exported, golden-tested live) and
lib/emit-fta.ts's renderFta()/gatePath()/markPath(). faultTree(): the top event is a
rectangle; under it a gate (AND / OR / k-of-n vote / inhibit) and the events that cause
it, down to basic events (circle), undeveloped events (diamond) and house events (house).
An event and the gate under it are one "compound node" laid out by lib/graph-layout.ts's
layoutTree() (a pure tree: a repeated event is drawn again, never joined) — already
ported in graph_layout.py for mindmap/tree. The only other auto-layout dependency is the
width-narrowing cascade, `fit_width.py`'s `narrow_cascade_fit()` (shared with bowtie.py).

NOT ported: ftaIds() (used only by the DSL layer to pre-validate connect() targets; this
port's anchors already come from layoutFta()'s own `anchors` list, same as every other
band) and ftaTexts() (a pre-registration list for Node's real text measurement — this
port measures synchronously via width_of, consistent with every other band here).

Golden master: lib/fta.ts + lib/emit-fta.ts + lib/fta-analysis.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import itertools
import math

from .atoms import WidthOf, text_width
from .badge import pill_svg
from .charts_base import _to_precision as to_precision
from .emit_boxes import render_box_rect
from .emit_common import emoji_span, js_num, js_round, snap4
from .fit_width import narrow_cascade_fit
from .fta_analysis import SHARED_LIMIT, fta_var, minimal_cut_sets, single_points, top_probability
from .graph_layout import layout_tree
from .tokens import PALETTE, color_of, tone_style
from .tree_text import measure_node, node_runs
from .wrap import WrapMode, wrap_text

FTA_KINDS = ["event", "basic", "undeveloped", "house", "condition"]
FTA_GATES = ["and", "or", "vote", "inhibit"]
_LEAVES = {"basic", "undeveloped", "house", "condition"}


def _to_exponential(x: float, digits: int) -> str:
    """JS ``x.toExponential(digits)``: Python's own ``%e`` formatting, with the C-style
    2-digit zero-padded exponent (``e-04``) stripped down to JS's bare form (``e-4``)."""
    s = f"{x:.{digits}e}"
    mantissa, exp = s.split("e")
    sign = exp[0]
    exp_digits = exp[1:].lstrip("0") or "0"
    return f"{mantissa}e{sign}{exp_digits}"


def fmt_p(p: float) -> str:
    """lib/fta.ts:42 fmtP(): 2 significant digits, exponent form below 0.001."""
    if p == 0:
        return "0"
    if p == 1:
        return "1"
    if p >= 0.995:
        return f"1 − {_to_exponential(1 - p, 1)}"
    if p >= 0.001:
        return js_num(to_precision(p, 2))
    return _to_exponential(p, 1)


_STATE_TEXT = {True: "常に発生すると仮定", False: "発生しないと仮定"}


def _state_sub(n: dict, quant: bool = False) -> str | None:
    """lib/fta.ts:43-47 stateSub()."""
    base = n.get("sub")
    if base is None and n["kind"] == "house" and n.get("state") is not None:
        base = _STATE_TEXT[n["state"]]
    if not quant or n.get("p") is None or n["kind"] == "house" or n.get("gate") is not None:
        return base
    return f"{base} (p = {fmt_p(n['p'])})" if base else f"p = {fmt_p(n['p'])}"


def fta_quant(root: dict, period: str | None = None) -> str:
    """lib/fta.ts:50-63 ftaQuant()."""
    missing: list[str] = []
    seen: set[str] = set()

    def scan(n: dict) -> None:
        if n.get("gate") is None and n["kind"] != "house" and n.get("p") is None and fta_var(n) not in seen:
            seen.add(fta_var(n))
            missing.append(f'"{n["label"]}"')
        for c in n.get("children") or []:
            scan(c)
        if n.get("cond"):
            scan(n["cond"])

    scan(root)
    if missing:
        raise ValueError(f"faultTree({{quant: true}}): these events have no p (a probability from 0 to 1): {', '.join(missing)}")
    result = top_probability(root)
    p, bound = result["p"], result["bound"]
    head = f"頂上事象の確率 ≦ {fmt_p(p)}（上限の概算。共有の基本事象が {SHARED_LIMIT} 個を超えたため min-cut upper bound）" if bound else f"頂上事象の確率 {fmt_p(p)}"
    return f"{f'期間: {period}。' if period else ''}{head}。基本事象は互いに独立と仮定"


def fta_resolve(top: dict) -> dict:
    """lib/fta.ts:79-162 ftaResolve(). Returns {"root": FtaNode, "nodes": [FtaNode, ...]}."""
    if not isinstance(top, dict):
        raise ValueError('faultTree(top) needs the top event: {label: "...", gate: "or", children: [...]}')

    defs: dict[str, dict] = {}

    def collect(e: dict, slot: str) -> None:
        if not isinstance(e, dict):
            raise ValueError("faultTree(): every event must be an object")
        if e.get("ref") is not None:
            return
        if e.get("id") is not None:
            if not isinstance(e["id"], str) or not e["id"]:
                raise ValueError(f'faultTree(): the id of "{e.get("label")}" must be a non-empty string')
            if e["id"] in defs:
                raise ValueError(f'faultTree(): duplicate event id "{e["id"]}"')
            defs[e["id"]] = {"ev": e, "slot": slot}
        if e.get("children") is not None and not isinstance(e["children"], list):
            raise ValueError(f'faultTree(): "{e.get("label")}": children must be an array')
        for c in e.get("children") or []:
            collect(c, "child")
        if e.get("condition") is not None:
            collect(e["condition"], "condition")

    collect(top, "top")

    def kind_of(e: dict, slot: str) -> str:
        k = e.get("kind")
        if k is None:
            k = "condition" if slot == "condition" else "event"
        if k not in FTA_KINDS:
            raise ValueError(f'faultTree(): "{e.get("label")}" has kind {k} (use {" | ".join(FTA_KINDS)})')
        return k

    def check(e: dict, slot: str) -> str:
        name = f'"{e.get("label")}"'
        kind = kind_of(e, slot)
        label = e.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("faultTree(): every event needs a label")
        p = e.get("p")
        if p is not None and not (isinstance(p, (int, float)) and not isinstance(p, bool) and 0 <= p <= 1):
            raise ValueError(f"faultTree(): {name}: p is a probability, a number from 0 to 1 (got {p})")
        if slot == "condition" and kind != "condition":
            raise ValueError(f"faultTree(): the condition of an inhibit gate {name} must be a condition event (kind: 'condition', or leave kind out)")
        if slot != "condition" and kind == "condition":
            raise ValueError(f"faultTree(): {name} is a condition event: it only goes in the `condition` of an inhibit gate")
        if slot == "top" and kind not in ("event", "basic", "undeveloped"):
            raise ValueError(f"faultTree(): the top event {name} cannot be a {kind} event")
        if kind == "event":
            children = e.get("children")
            if e.get("gate") is None or not children:
                raise ValueError(f"faultTree(): {name} needs a gate and children (an event that goes no further is kind: 'undeveloped' or 'basic')")
            if e["gate"] not in FTA_GATES:
                raise ValueError(f'faultTree(): {name} has gate {e["gate"]} (use {" | ".join(FTA_GATES)})')
            if e.get("state") is not None:
                raise ValueError(f"faultTree(): {name}: state is for a house event")
            if e.get("p") is not None:
                raise ValueError(f"faultTree(): {name} has a gate: its probability is worked out from its inputs, p goes on the basic events")
            if e["gate"] == "vote":
                n_inputs = len(children)
                k = e.get("k")
                if not (isinstance(k, int) and not isinstance(k, bool) and 1 <= k <= n_inputs):
                    raise ValueError(f"faultTree(): {name}: a vote gate needs k, a whole number from 1 to the number of inputs ({n_inputs}); got {k}")
            elif e.get("k") is not None:
                raise ValueError(f"faultTree(): {name}: k is for a vote gate")
            if e["gate"] == "inhibit":
                if len(children) != 1:
                    raise ValueError(f"faultTree(): {name}: an inhibit gate has one input in children (got {len(children)}) and one condition")
                if e.get("condition") is None:
                    raise ValueError(f"faultTree(): {name}: an inhibit gate needs a condition")
            elif e.get("condition") is not None:
                raise ValueError(f"faultTree(): {name}: condition is for an inhibit gate")
        else:
            for f in ("gate", "children", "condition", "k"):
                if e.get(f) is not None:
                    raise ValueError(f"faultTree(): {name} is a {kind} event: it takes no {f}")
            if kind == "house":
                if not isinstance(e.get("state"), bool):
                    raise ValueError(f"faultTree(): the house event {name} needs state: true (it always happens) or false (it never does)")
                if e.get("p") is not None:
                    raise ValueError(f"faultTree(): the house event {name} takes no p (its state says whether it happens)")
            elif e.get("state") is not None:
                raise ValueError(f"faultTree(): {name}: state is for a house event")
        return kind

    counter = itertools.count()
    nodes: list[dict] = []

    def build(e: dict, slot: str) -> dict:
        src, src_slot, copy_of = e, slot, None
        if e.get("ref") is not None:
            extra = [k for k in e if k != "ref"]
            if extra:
                raise ValueError(f'faultTree(): {{ref: "{e["ref"]}"}} takes no other field ({", ".join(extra)}): write them on the event it repeats')
            d = defs.get(e["ref"])
            if d is None:
                raise ValueError(f'faultTree(): {{ref: "{e["ref"]}"}} names no event (ids: {", ".join(defs.keys()) or "none"})')
            k = kind_of(d["ev"], d["slot"])
            if k not in _LEAVES:
                raise ValueError(f'faultTree(): {{ref: "{e["ref"]}"}} repeats an event with a gate under it; only a basic, undeveloped, house or condition event can be repeated')
            if (k == "condition") != (slot == "condition"):
                msg = "a condition event: it only goes in the `condition` of an inhibit gate" if k == "condition" else "not a condition event: the condition of an inhibit gate must be one"
                raise ValueError(f'faultTree(): {{ref: "{e["ref"]}"}} is {msg}')
            src, src_slot, copy_of = d["ev"], d["slot"], e["ref"]
        kind = check(src, src_slot)
        node: dict = {"key": f"n{next(counter)}", "label": src["label"], "kind": kind, "children": []}
        if src.get("sub") is not None:
            node["sub"] = src["sub"]
        if copy_of is not None:
            node["copyOf"] = copy_of
        elif src.get("id") is not None:
            node["id"] = src["id"]
        if src.get("gate") is not None:
            node["gate"] = src["gate"]
        if src.get("k") is not None:
            node["k"] = src["k"]
        if src.get("state") is not None:
            node["state"] = src["state"]
        if src.get("p") is not None:
            node["p"] = src["p"]
        nodes.append(node)
        if copy_of is None:
            node["children"] = [build(c, "child") for c in (src.get("children") or [])]
            if src.get("condition") is not None:
                node["cond"] = build(src["condition"], "condition")
        return node

    root = build(top, "top")
    return {"root": root, "nodes": nodes}


_SINGLE_TEXT = {"basic": "単一故障点", "undeveloped": "未展開・単独で頂上へ"}


def _single_text(n: dict) -> str | None:
    """lib/fta.ts:165-166 singleText()."""
    return _SINGLE_TEXT.get(n["kind"]) if n.get("gate") is None and n["kind"] in _SINGLE_TEXT else None


def fta_single_points(root: dict) -> set[str]:
    """lib/fta.ts:169-173 ftaSinglePoints()."""
    cuts = minimal_cut_sets(root)
    if cuts["truncated"]:
        raise ValueError("faultTree({cutSets: true}): the tree has too many cut sets to find the single points of failure; simplify the tree (fewer vote gates, fewer events under an AND of ORs)")
    return single_points(cuts)


def fta_band(top: dict, *, max_node_w: float | str | None = None, cut_sets: bool | None = None, quant: bool | None = None, quant_period: str | None = None, id: str | None = None) -> dict:
    """lib/dsl/diagrams.ts:496-506 faultTree() (the band-construction half; this port has no
    separate ftaBand() export to mirror — Node builds it inline in the DSL function)."""
    if max_node_w is not None and max_node_w != "auto" and not (isinstance(max_node_w, (int, float)) and max_node_w >= 80):
        raise ValueError(f"faultTree(): maxNodeW must be a number >= 80 or 'auto' (got {max_node_w!r})")
    root = fta_resolve(top)["root"]  # every mistake in the tree throws here, naming the event
    if cut_sets:
        fta_single_points(root)  # throws when the tree has too many cut sets to find them
    if quant_period is not None and (not isinstance(quant_period, str) or not quant_period.strip() or not quant):
        raise ValueError("faultTree(): quantPeriod is a non-empty string, and goes with quant: true")
    if quant:
        fta_quant(root, quant_period)  # throws for an event without p
    band: dict = {"type": "fta", "root": top}
    if max_node_w is not None:
        band["maxNodeW"] = max_node_w
    if cut_sets is not None:
        band["cutSets"] = cut_sets
    if quant is not None:
        band["quant"] = quant
    if quant_period is not None:
        band["quantPeriod"] = quant_period
    if id is not None:
        band["id"] = id
    return band


NOTE_GAP = 16
BADGE_GAP, BADGE_PAD_X, BADGE_H = 6, 10, 22
STEM, GATE_W, GATE_H, MARK_W, MARK_H, COND_MARK_W, COND_MARK_H, COND_GAP, GAP, LEVEL_GAP = 10, 40, 36, 26, 26, 40, 24, 22, 24, 36


def layout_fta(band: dict, x: float, y: float, w: float, width_of: WidthOf, roles: dict, mode: WrapMode, space: float = 1) -> dict:
    """lib/fta.ts:215-313 layoutFta()."""
    root = fta_resolve(band["root"])["root"]
    single = fta_single_points(root) if band.get("cutSets") else set()

    def attempt(max_w: float, floor: bool) -> dict:
        comps: dict[str, dict] = {}

        def measure(n: dict) -> dict:
            sub = _state_sub(n, band.get("quant", False))
            lines = measure_node(n["label"], sub, max_w, width_of, roles, mode, floor)
            c: dict = {"node": n, "lines": lines, "rect": {"w": lines["w"], "h": lines["h"]}, "w": lines["w"], "h": 0, "outY": 0}
            if n.get("gate") is not None:
                below = GATE_H
                if n.get("cond"):
                    cl = measure_node(n["cond"]["label"], _state_sub(n["cond"], band.get("quant", False)), max_w, width_of, roles, mode, floor)
                    c["cond"] = {"node": n["cond"], "lines": cl, "w": cl["w"], "h": cl["h"]}
                    below = max(GATE_H, cl["h"] + STEM + COND_MARK_H)
                    c["w"] = max(c["w"], GATE_W + 2 * (COND_GAP + cl["w"]))
                c["w"] = max(c["w"], GATE_W)
                c["outY"] = c["rect"]["h"] + STEM + (GATE_H * 0.83 if n["gate"] in ("or", "vote") else GATE_H)
                c["h"] = c["rect"]["h"] + STEM + below
            else:
                c["w"] = max(c["w"], MARK_W)
                leaf_h = c["rect"]["h"] + STEM + MARK_H
                c["h"] = leaf_h
                c["outY"] = leaf_h
                bt = _single_text(n) if fta_var(n) in single else None
                if bt:
                    c["badge"] = {"text": bt, "w": math.ceil(text_width(width_of, bt, roles["note"], 700)) + 2 * BADGE_PAD_X}
                    c["w"] = max(c["w"], c["badge"]["w"])
                    c["h"] += BADGE_GAP + BADGE_H
            comps[n["key"]] = c
            for k in n["children"]:
                measure(k)
            return c

        measure(root)

        def to_tree(n: dict) -> dict:
            sz = comps[n["key"]]
            node: dict = {"id": n["key"], "size": {"w": sz["w"], "h": sz["h"]}}
            if n["children"]:
                node["children"] = [to_tree(c) for c in n["children"]]
            return node

        tree = layout_tree(to_tree(root), dir="down", gap=js_round(GAP * space), level_gap=js_round(LEVEL_GAP * space))
        return {"size": {"w": tree["w"], "h": tree["h"]}, "score": {"crossings": 0, "bends": 0}, "comps": comps, "tree": tree}

    auto = band.get("maxNodeW") == "auto"
    written = band["maxNodeW"] if isinstance(band.get("maxNodeW"), (int, float)) else None
    fitted = narrow_cascade_fit(
        who="faultTree()", w=w, max_node_w=written, mode="auto" if auto else "omitted",
        build=lambda max_w, floor: attempt(max_w, floor),
        fix="a wider figure (diagram({width})), or a smaller tree",
    )
    tree, comps = fitted["result"]["tree"], fitted["result"]["comps"]
    dx, dy = x + (w - tree["w"]) / 2, y
    out: dict = {
        "type": "fta", "x": x, "y": y, "w": w, "h": tree["h"],
        "nodes": [], "marks": [], "badges": [], "gates": [], "edges": [], "texts": [], "anchors": [], "labelBoxes": [],
    }
    if band.get("id") is not None:
        out["id"] = band["id"]
    if band.get("reveal") is not None:
        out["reveal"] = band["reveal"]
    if band.get("until") is not None:
        out["until"] = band["until"]
    if fitted["applied"]:
        out["fitApplied"] = fitted["applied"]

    def place(n: dict, px: float, py: float, pw: float, cl: dict, rw: float, rh: float) -> dict:
        r = {"x": px + (pw - rw) / 2, "y": py, "w": rw, "h": rh}
        node_entry = {**r, "kind": n["kind"]}
        if n.get("id") is not None:
            node_entry["id"] = n["id"]
            out["anchors"].append({"id": n["id"], **r})
        out["nodes"].append(node_entry)
        out["labelBoxes"].append({"label": n["label"], **r})
        out["texts"].extend(node_runs(r, cl, roles))
        return r

    def cx_of(p: dict) -> float:
        return p["x"] + p["w"] / 2

    def seg(a: dict, b: dict) -> None:
        out["edges"].append({"points": [a, b]})

    for key, p in tree["nodes"].items():
        c = comps[key]
        n = c["node"]
        px, py = p["x"] + dx, p["y"] + dy
        mid = px + p["w"] / 2
        r = place(n, px, py, p["w"], c["lines"], c["rect"]["w"], c["rect"]["h"])
        if n.get("gate") is None:
            m = {"x": mid - MARK_W / 2, "y": r["y"] + r["h"] + STEM, "w": MARK_W, "h": MARK_H}
            mark_entry = {**m, "kind": n["kind"]}
            if c.get("badge"):
                mark_entry["single"] = True
            out["marks"].append(mark_entry)
            seg({"x": mid, "y": r["y"] + r["h"]}, {"x": mid, "y": m["y"]})
            if c.get("badge"):
                out["badges"].append({"x": mid - c["badge"]["w"] / 2, "y": m["y"] + m["h"] + BADGE_GAP, "w": c["badge"]["w"], "h": BADGE_H, "text": c["badge"]["text"], "size": roles["note"]})
            continue
        g = {"x": mid - GATE_W / 2, "y": r["y"] + r["h"] + STEM, "w": GATE_W, "h": GATE_H}
        gate_entry = {**g, "gate": n["gate"]}
        if n["gate"] == "vote":
            gate_entry["label"] = {"text": f"{n['k']}/{len(n['children'])}", "size": roles["note"]}
        out["gates"].append(gate_entry)
        seg({"x": mid, "y": r["y"] + r["h"]}, {"x": mid, "y": g["y"]})
        if c.get("cond"):
            cr = {"x": g["x"] + g["w"] + COND_GAP, "y": g["y"]}
            cr2 = place(c["cond"]["node"], cr["x"], cr["y"], c["cond"]["w"], c["cond"]["lines"], c["cond"]["w"], c["cond"]["h"])
            m = {"x": cx_of(cr2) - COND_MARK_W / 2, "y": cr2["y"] + cr2["h"] + STEM, "w": COND_MARK_W, "h": COND_MARK_H}
            out["marks"].append({**m, "kind": "condition"})
            seg({"x": cx_of(cr2), "y": cr2["y"] + cr2["h"]}, {"x": cx_of(cr2), "y": m["y"]})
            ly = min(max(g["y"] + GATE_H / 2, cr2["y"] + 8), cr2["y"] + cr2["h"] - 8)
            seg({"x": g["x"] + g["w"], "y": ly}, {"x": cr2["x"], "y": ly})

    for e in tree["edges"]:
        from_comp = comps[e["from"]]
        pts = [{"x": q["x"] + dx, "y": q["y"] + dy} for q in e["points"]]
        pts[0] = {"x": pts[0]["x"], "y": tree["nodes"][e["from"]]["y"] + dy + from_comp["outY"]}
        out["edges"].append({"points": pts})

    if band.get("quant"):
        note = fta_quant(root, band.get("quantPeriod"))
        lh = js_round(roles["note"] * 1.4)
        lines = wrap_text(note, max_width=w, atom_width=lambda a: width_of(a, roles["note"], 400, "sans"), mode=mode)
        out["note"] = note
        for i, t in enumerate(lines):
            out["texts"].append({"text": t, "x": x + w / 2, "y": y + tree["h"] + NOTE_GAP + i * lh + roles["note"], "size": roles["note"], "bold": False, "muted": True})
        out["h"] = tree["h"] + NOTE_GAP + len(lines) * lh

    return out


def gate_path(gate: str, r: dict) -> str:
    """lib/emit-fta.ts:15-20 gatePath()."""
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]
    mx = x + w / 2
    n = snap4
    if gate == "and":
        return f"M{n(x)},{n(y + h)} V{n(y + h * 0.45)} A{n(w / 2)},{n(h * 0.45)} 0 0 1 {n(x + w)},{n(y + h * 0.45)} V{n(y + h)} Z"
    if gate == "inhibit":
        return f"M{n(mx)},{n(y)} L{n(x + w)},{n(y + h * 0.25)} L{n(x + w)},{n(y + h * 0.75)} L{n(mx)},{n(y + h)} L{n(x)},{n(y + h * 0.75)} L{n(x)},{n(y + h * 0.25)} Z"
    return f"M{n(x)},{n(y + h)} Q{n(mx)},{n(y + h * 0.66)} {n(x + w)},{n(y + h)} Q{n(x + w)},{n(y + h * 0.32)} {n(mx)},{n(y)} Q{n(x)},{n(y + h * 0.32)} {n(x)},{n(y + h)} Z"


def mark_path(kind: str, r: dict) -> str:
    """lib/emit-fta.ts:23-29 markPath()."""
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]
    n = snap4
    cx, cy = x + w / 2, y + h / 2
    if kind == "undeveloped":
        return f"M{n(cx)},{n(y)} L{n(x + w)},{n(cy)} L{n(cx)},{n(y + h)} L{n(x)},{n(cy)} Z"
    if kind == "house":
        return f"M{n(x)},{n(y + h)} V{n(y + h * 0.4)} L{n(cx)},{n(y)} L{n(x + w)},{n(y + h * 0.4)} V{n(y + h)} Z"
    rx = w / 2 if kind == "condition" else min(w, h) / 2
    ry = h / 2
    return f"M{n(cx - rx)},{n(cy)} A{n(rx)},{n(ry)} 0 1 0 {n(cx + rx)},{n(cy)} A{n(rx)},{n(ry)} 0 1 0 {n(cx - rx)},{n(cy)} Z"


def render_fta(b: dict, day: int | str = 1) -> str:
    """lib/emit-fta.ts:40-57 renderFta()."""
    out = []
    dim = bool(b.get("dim"))
    ink = PALETTE["muted"] if dim else PALETTE["text"]
    for e in b["edges"]:
        pts = " L".join(f"{snap4(p['x'])},{snap4(p['y'])}" for p in e["points"])
        out.append(f'<path d="M{pts}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="2"/>')
    for g in b["gates"]:
        out.append(f'<path d="{gate_path(g["gate"], g)}" fill="{PALETTE["bg"]}" stroke="{ink}" stroke-width="2"/>')
        if g.get("label"):
            out.append(f'<text x="{js_round(g["x"] + g["w"] / 2)}" y="{js_round(g["y"] + g["h"] * 0.72)}" text-anchor="middle" font-size="{g["label"]["size"]}" fill="{ink}">{emoji_span(g["label"]["text"])}</text>')
    alert = PALETTE["muted"] if dim else PALETTE["danger"]
    for m in b["marks"]:
        sw = 4 if m.get("single") else 2
        out.append(f'<path d="{mark_path(m["kind"], m)}" fill="{PALETTE["bg"]}" stroke="{alert if m.get("single") else ink}" stroke-width="{sw}"/>')
    for t in b["badges"]:
        x0, y0 = snap4(t["x"]), snap4(t["y"])
        x1 = snap4(t["x"] + t["w"])
        out.append(pill_svg(x=x0, y=y0, w=x1 - x0, h=t["h"], fill=alert, cx=t["x"] + t["w"] / 2, baseline=t["y"] + t["h"] / 2 + t["size"] * 0.36, raw_y=t["y"], text=PALETTE["bg"], size=t["size"], label_html=emoji_span(t["text"])))
    for n in b["nodes"]:
        out.append(render_box_rect(x=n["x"], y=n["y"], w=n["w"], h=n["h"], tone="plain", dim=dim, day=day, default_tone="plain"))
    for t in b["texts"]:
        fill = PALETTE["muted"] if dim else (PALETTE["muted"] if t["muted"] else color_of(tone_style("plain").text, day))
        weight = ' font-weight="700"' if t["bold"] else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}" text-anchor="middle" font-size="{t["size"]}"{weight} fill="{fill}">{emoji_span(t["text"])}</text>')
    return "\n  ".join(out)
