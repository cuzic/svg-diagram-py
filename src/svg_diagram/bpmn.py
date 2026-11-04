"""1:1 port of lib/bpmn.ts's layoutBpmn() (exported, golden-tested live) and
lib/emit-figures.ts's renderBpmn(): a business flow in lanes (pools' lanes), BPMN-style —
tasks, start/end events and gateways (exclusive/parallel/inclusive), joined by sequence
flows (solid) and message flows (dashed). Lanes are given; the columns come from the flow
(graph_layout.py's layout_layered, for the layer of each node, already ported for
states/classes/bpmn/cause/pert/causalLoop/dependencyNetwork — see BANDS.md's Tier 3
note), the rows from the lane. When no fixed shape clears the boxes, a route is searched
with orthogonal_route.py's route_clear (also already ported).

NOT ported: a task's `icon`/`iconTone` (an installed SVG icon above the label) — the icon
registry itself is not ported in this port (same reason box()'s renderBoxIcon is out of
scope; sankey()'s node icons are likewise skipped). bpmn_band() raises NotImplementedError
if a node sets either.

Golden master: lib/bpmn.ts + lib/emit-figures.ts's renderBpmn() (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import text_width
from .emit_common import _sign, emoji_span, js_num, js_round, snap4
from .graph_layout import layout_layered
from .orthogonal_route import route_clear
from .tokens import PALETTE, color_of, resolve_box_style, tone_style
from .tree_text import line_h, measure_node, narrow_texts, node_runs
from .wrap import wrap_text
from .emit_boxes import render_box_rect

LABEL_COL, PAD_Y, COL_GAP, EVENT, GATE, TASK_MAX, LABEL_MAX, STUB, CHIP_PAD = 120, 22, 52, 36, 44, 168, 120, 16, 5
BPMN_KINDS = ["task", "start", "end", "xor", "and", "or"]


def _is_event(k: str) -> bool:
    return k in ("start", "end")


def _is_gate(k: str) -> bool:
    return k in ("xor", "and", "or")


def bpmn_band(
    lanes: list[dict], nodes: list[dict], flows: list[dict], *, fit: str | None = None, id: str | None = None, reveal: float | None = None, until: float | None = None
) -> dict:
    """lib/dsl/diagrams.ts:68-82 bpmn()."""
    if not lanes:
        raise ValueError("bpmn(lanes, nodes, flows) needs at least one lane")
    if not nodes:
        raise ValueError("bpmn(lanes, nodes, flows) needs at least one node")
    for n in nodes:
        if n.get("icon") is not None or n.get("iconTone") is not None:
            raise NotImplementedError(
                f"bpmn(): node \"{n.get('id')}\" sets icon/iconTone, but this port does not implement the icon registry "
                "(same reason box()'s icon is out of scope)"
            )
    for f in flows:
        if f.get("line") is not None and f["line"] not in ("solid", "dashed"):
            raise ValueError(f"bpmn(): flow {f['from']} -> {f['to']} has line {f['line']}")
    if fit is not None and fit != "shrink":
        raise ValueError(f"bpmn(): fit must be 'shrink' (got {fit})")
    band: dict = {"type": "bpmn", "lanes": list(lanes), "nodes": list(nodes), "flows": list(flows)}
    if id is not None:
        band["id"] = id
    if fit is not None:
        band["fit"] = fit
    if reveal is not None:
        band["reveal"] = reveal
    if until is not None:
        band["until"] = until
    return band


# fit: 'shrink' tries these in order until the figure fits: narrower lane-name column, tighter column gaps, narrower task boxes.
SHRINK_STEPS: list[dict] = [
    {"labelCol": LABEL_COL, "colGap": COL_GAP, "taskMax": TASK_MAX, "flowRoom": 2 * STUB},
    {"labelCol": 96, "colGap": 36, "taskMax": 140, "flowRoom": STUB},
    {"labelCol": 80, "colGap": 28, "taskMax": 116, "flowRoom": 0},
    {"labelCol": 64, "colGap": 22, "taskMax": 96, "flowRoom": None},
    {"labelCol": 64, "colGap": 16, "taskMax": 80, "flowRoom": None},
]


def layout_bpmn(band: dict, x: float, y: float, w: float, width_of, roles: dict, mode: str = "phrase", space: float = 1) -> dict:
    """lib/bpmn.ts:42-46 layoutBpmn()."""
    env = {"wrap": mode, "keepWords": False, "space": space}
    steps = SHRINK_STEPS if band.get("fit") == "shrink" else SHRINK_STEPS[:1]
    for m in steps[:-1]:
        out = _layout_bpmn_at(band, x, y, w, width_of, roles, env, m, False)
        if out is not None:
            return out
    result = _layout_bpmn_at(band, x, y, w, width_of, roles, env, steps[-1], True)
    assert result is not None  # _layout_bpmn_at() only returns None via its "if not final: return None" bailout
    return result


def _layout_bpmn_at(band: dict, x: float, y: float, w: float, width_of, roles: dict, env: dict, metrics: dict, final: bool) -> dict | None:
    """lib/bpmn.ts:50-312 layoutBpmnAt()."""
    label_col, task_max, flow_room = metrics["labelCol"], metrics["taskMax"], metrics["flowRoom"]
    col_gap = js_round(metrics["colGap"] * env.get("space", 1))
    B, S = roles["body"], roles["note"]
    lane_idx = {l["id"]: i for i, l in enumerate(band["lanes"])}
    if len(lane_idx) != len(band["lanes"]):
        raise ValueError("bpmn(): duplicate lane id")
    ids: set[str] = set()
    for n in band["nodes"]:
        if not isinstance(n.get("id"), str) or not n["id"]:
            raise ValueError("bpmn(): every node needs an id")
        if n["id"] in ids:
            raise ValueError(f'bpmn(): duplicate node id "{n["id"]}"')
        ids.add(n["id"])
        if n["lane"] not in lane_idx:
            raise ValueError(f'bpmn(): node "{n["id"]}" uses unknown lane "{n["lane"]}"')
        k = n.get("kind", "task")
        if k not in BPMN_KINDS:
            raise ValueError(f'bpmn(): node "{n["id"]}" has kind {k} (use {" | ".join(BPMN_KINDS)})')
        if k == "task" and not (n.get("label") or "").strip():
            raise ValueError(f'bpmn(): task "{n["id"]}" needs a label')
    for f in band["flows"]:
        for e in (f["from"], f["to"]):
            if e not in ids:
                raise ValueError(f'bpmn(): flow {f["from"]} -> {f["to"]} names unknown node "{e}"')
    kind_of = {n["id"]: n.get("kind", "task") for n in band["nodes"]}
    for f in band["flows"]:
        if kind_of.get(f["to"]) == "start":
            raise ValueError(
                f'bpmn(): flow {f["from"]} -> {f["to"]}: a start event takes no flow into it '
                "(a message start event is not drawn; start from a task instead)"
            )
        if kind_of.get(f["from"]) == "end":
            raise ValueError(f'bpmn(): flow {f["from"]} -> {f["to"]}: an end event has no flow out of it')

    # size of each node (the shape; an event / gateway label hangs below it)
    meas: dict[str, dict] = {}
    for n in band["nodes"]:
        k = kind_of[n["id"]]
        if k == "task":
            m = measure_node(n["label"], n.get("sub"), task_max, width_of, roles, env["wrap"], env.get("keepWords", False), keep_words_cap=168 - 28)
            meas[n["id"]] = {"w": m["w"], "h": m["h"], "lines": m, "label": [], "extent": m["h"]}
            continue
        size = EVENT if _is_event(k) else GATE
        label = wrap_text(n["label"], max_width=LABEL_MAX, atom_width=lambda a: width_of(a, B, 400, "sans"), mode=env["wrap"]) if n.get("label") else []
        meas[n["id"]] = {"w": size, "h": size, "label": label, "extent": size + (4 + len(label) * line_h(B) if label else 0)}

    def label_width(m: dict) -> float:
        best = m["w"]
        for ln in m["label"]:
            best = max(best, math.ceil(text_width(width_of, ln, B, 400)))
        return best

    # columns: the layer of each node along the flow (starts first)
    lay = layout_layered(
        [{"id": n["id"], "size": {"w": meas[n["id"]]["w"], "h": meas[n["id"]]["h"]}} for n in band["nodes"]],
        [{"from": f["from"], "to": f["to"]} for f in band["flows"]],
        {"start": [n["id"] for n in band["nodes"] if kind_of[n["id"]] == "start"], "tighten": False},
    )
    n_layers = max(lay["layers"].values()) + 1
    col_w = [0.0] * n_layers
    for n in band["nodes"]:
        c = lay["layers"][n["id"]]
        col_w[c] = max(col_w[c], label_width(meas[n["id"]]))
    widest_flow = 0.0
    for f in band["flows"]:
        if f.get("label"):
            widest_flow = max(widest_flow, math.ceil(text_width(width_of, f["label"], S, 400)) + 2 * CHIP_PAD)
    gap = col_gap if flow_room is None else max(col_gap, widest_flow + flow_room)
    col_x: list[float] = []
    a = x + label_col + gap / 2
    for cw in col_w:
        col_x.append(a)
        a += cw + gap
    total = col_x[n_layers - 1] + col_w[n_layers - 1] + gap / 2 - x
    if total > w + 0.5:
        if not final:
            return None
        hint = "even shrunk; " if band.get("fit") == "shrink" else "set fit: 'shrink', "
        raise ValueError(f"bpmn(): the figure is {math.ceil(total)}px wide but it has {js_round(w)}px ({hint}merge steps, shorten labels, or split the flow into two figures)")
    width = w

    # rows: each lane is as tall as its tallest stack of nodes that share a column
    stacks: dict[str, list[str]] = {}
    for n in band["nodes"]:
        key = f"{lane_idx[n['lane']]}:{lay['layers'][n['id']]}"
        stacks.setdefault(key, []).append(n["id"])
    lane_lines = [wrap_text(l["label"], max_width=label_col - 16, atom_width=lambda a: width_of(a, B, 700, "sans"), mode=env["wrap"]) for l in band["lanes"]]
    lane_h: list[float] = []
    for li in range(len(band["lanes"])):
        h = len(lane_lines[li]) * line_h(B) + 2 * PAD_Y
        for key, lst in stacks.items():
            if not key.startswith(f"{li}:"):
                continue
            if len(lst) == 1:
                m = meas[lst[0]]
                block = m["extent"] - m["h"]
                h = max(h, 2 * (m["h"] / 2 + block))
            else:
                s = 0.0
                for i, node_id in enumerate(lst):
                    s += meas[node_id]["extent"] + (16 if i else 0)
                h = max(h, s)
        lane_h.append(max(88, h + 2 * PAD_Y, len(lane_lines[li]) * line_h(B) + 2 * PAD_Y))
    lane_top: list[float] = []
    acc = y
    for h in lane_h:
        lane_top.append(acc)
        acc += h

    out: dict = {"type": "bpmn", "x": x, "y": y, "w": width, "h": sum(lane_h), "lanes": [], "nodes": [], "icons": [], "edges": [], "texts": [], "labels": [], "anchors": [], "labelBoxes": []}
    if band.get("fit") == "shrink":
        task_lines = [meas[n["id"]]["lines"]["label"] for n in band["nodes"] if kind_of[n["id"]] == "task"]
        narrow = narrow_texts(task_lines)
        if narrow:
            out["narrow"] = narrow
    if band.get("id") is not None:
        out["id"] = band["id"]
    if band.get("reveal") is not None:
        out["reveal"] = band["reveal"]
    if band.get("until") is not None:
        out["until"] = band["until"]

    for i, l in enumerate(band["lanes"]):
        out["lanes"].append({"x": x, "y": lane_top[i], "w": width, "h": lane_h[i], "labelW": label_col, "tone": l.get("tone", "plain")})
        lines = lane_lines[i]
        top = lane_top[i] + lane_h[i] / 2 - (len(lines) * line_h(B)) / 2
        for k, ln in enumerate(lines):
            out["texts"].append({"text": ln, "x": x + label_col / 2, "y": top + k * line_h(B) + B, "size": B, "bold": True, "muted": False, "anchor": "middle"})

    # place nodes: column centre, stacked and centred in the lane
    rect: dict[str, dict] = {}
    for key, lst in stacks.items():
        li, c = (int(v) for v in key.split(":"))
        first = lst[0]
        top0, high = lane_top[li], lane_h[li]
        total_extent = 0.0
        for i, node_id in enumerate(lst):
            total_extent += meas[node_id]["extent"] + (16 if i else 0)
        ty = (top0 + high / 2 - meas[first]["h"] / 2) if len(lst) == 1 else (top0 + (high - total_extent) / 2)
        if len(lst) > 1 and _is_gate(kind_of[first]):
            ty += meas[first]["extent"] - meas[first]["h"]
        cx = col_x[c] + col_w[c] / 2
        for node_id in lst:
            m = meas[node_id]
            rect[node_id] = {"x": cx - m["w"] / 2, "y": ty, "w": m["w"], "h": m["h"]}
            ty += m["extent"] + 16

    event_labels: list[dict] = []  # the names that hang below events: flows keep off them too
    label_of_node: set[int] = set()  # the nodes' own boxes in labelBoxes (checked as rects, not as labels)
    for n in band["nodes"]:
        r, m, k = rect[n["id"]], meas[n["id"]], kind_of[n["id"]]
        out["nodes"].append({**r, "kind": k, "tone": n.get("tone", "plain")})
        out["anchors"].append({"id": n["id"], **r})
        nb = {"label": n.get("label") or n["id"], "x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]}
        out["labelBoxes"].append(nb)
        label_of_node.add(id(nb))
        if m.get("lines"):
            for t in node_runs(r, m["lines"], roles):
                out["texts"].append({**t, "anchor": "middle"})
        elif not _is_gate(k):  # an event's label hangs below it (a gateway's is placed after the flows are known)
            for i, ln in enumerate(m["label"]):
                tw = math.ceil(text_width(width_of, ln, B, 400))
                ty = r["y"] + r["h"] + 4 + i * line_h(B) + B
                out["texts"].append({"text": ln, "x": r["x"] + r["w"] / 2, "y": ty, "size": B, "bold": False, "muted": False, "anchor": "middle"})
                out["labelBoxes"].append({"label": ln, "x": r["x"] + r["w"] / 2 - tw / 2, "y": ty - B, "w": tw, "h": B + 4})
                event_labels.append({"x": r["x"] + r["w"] / 2 - tw / 2, "y": ty - B, "w": tw, "h": B + 4})

    # flows
    def hit(a: dict, b: dict) -> bool:
        return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]

    def seg_box(p: dict, q: dict) -> dict:
        return {"x": min(p["x"], q["x"]) - 1, "y": min(p["y"], q["y"]) - 1, "w": abs(p["x"] - q["x"]) + 2, "h": abs(p["y"] - q["y"]) + 2}

    def through(pts: list[dict], skip: list[str]) -> bool:
        for i in range(len(pts) - 1):
            b = seg_box(pts[i], pts[i + 1])
            if any(node_id not in skip and hit(b, r) for node_id, r in rect.items()):
                return True
            if any(hit(b, r) for r in event_labels):
                return True
        return False

    def simplify(pts: list[dict]) -> list[dict]:
        o: list[dict] = []
        for p in pts:
            if not o or abs(o[-1]["x"] - p["x"]) > 0.01 or abs(o[-1]["y"] - p["y"]) > 0.01:
                o.append(p)

        def keep(i: int, p: dict) -> bool:
            if i == 0 or i == len(o) - 1:
                return True
            prev, nxt = o[i - 1], o[i + 1]
            return not ((prev["x"] == p["x"] and p["x"] == nxt["x"]) or (prev["y"] == p["y"] and p["y"] == nxt["y"]))

        return [p for i, p in enumerate(o) if keep(i, p)]

    def lane_of(node_id: str) -> int:
        return lane_idx[next(n for n in band["nodes"] if n["id"] == node_id)["lane"]]

    def col_of(node_id: str) -> int:
        return lay["layers"][node_id]

    def search(a: str, b: str) -> list[dict] | None:
        r = route_clear(
            {
                "from": rect[a],
                "to": rect[b],
                "boxes": [*rect.values(), *event_labels],
                "bounds": {"x": x + label_col, "y": y, "w": width - label_col, "h": out["h"]},
                "others": [e["points"] for e in out["edges"]],
                "xs": [v for c, cx in enumerate(col_x) for v in (cx - gap / 2, cx + col_w[c] + gap / 2)],
                "ys": [v for li, t in enumerate(lane_top) for v in (t + 8, t + lane_h[li] - 8)],
            }
        )
        return simplify(r) if r else None

    col_seen: dict[int, int] = {}
    pending: list[tuple[int, str, list[dict]]] = []
    for fi, f in enumerate(band["flows"]):
        A, Bx = rect[f["from"]], rect[f["to"]]
        ca = {"x": A["x"] + A["w"] / 2, "y": A["y"] + A["h"] / 2}
        cb = {"x": Bx["x"] + Bx["w"] / 2, "y": Bx["y"] + Bx["h"] / 2}
        line = "dashed" if f.get("line") == "dashed" else "solid"
        if f["from"] == f["to"]:
            pts = [
                {"x": A["x"] + A["w"], "y": ca["y"] - 8},
                {"x": A["x"] + A["w"] + 22, "y": ca["y"] - 8},
                {"x": A["x"] + A["w"] + 22, "y": ca["y"] + 8},
                {"x": A["x"] + A["w"], "y": ca["y"] + 8},
            ]
        elif Bx["x"] > A["x"] + A["w"] - 1:  # forward: out of the right (or the top / bottom vertex of a gateway), into the left
            gate = _is_gate(kind_of[f["from"]])
            same_row = abs(ca["y"] - cb["y"]) < 1
            k = col_seen.get(col_of(f["to"]), 0)
            col_seen[col_of(f["to"])] = k + 1
            xm = Bx["x"] - STUB - (k % 3) * 8
            end = {"x": Bx["x"], "y": cb["y"]}
            if same_row:
                pts = [{"x": A["x"] + A["w"], "y": ca["y"]}, end]
            elif gate:
                pts = [{"x": ca["x"], "y": A["y"] if cb["y"] < ca["y"] else A["y"] + A["h"]}, {"x": ca["x"], "y": cb["y"]}, end]
            else:
                pts = [{"x": A["x"] + A["w"], "y": ca["y"]}, {"x": xm, "y": ca["y"]}, {"x": xm, "y": cb["y"]}, end]
            pts = simplify(pts)
            if not gate and not same_row and through(pts, [f["from"], f["to"]]):  # an event's name hangs wider than the event: turn further left, clear of it, before detouring
                col_left = col_x[col_of(f["to"])]
                sx = xm - 4
                lower_bound = max(col_left - gap / 2, A["x"] + A["w"]) + 4
                while sx > lower_bound:
                    t = simplify([{"x": A["x"] + A["w"], "y": ca["y"]}, {"x": sx, "y": ca["y"]}, {"x": sx, "y": cb["y"]}, end])
                    if not through(t, [f["from"], f["to"]]):
                        pts = t
                        break
                    sx -= 4
            if through(pts, [f["from"], f["to"]]):  # something stands in the way: run along a lane's edge, turning in a gap between columns
                cf, ct = col_of(f["from"]), col_of(f["to"])
                start = {"x": A["x"] + A["w"], "y": ca["y"]}
                channels = [
                    lane_top[lane_of(f["to"])] + 8,
                    lane_top[lane_of(f["to"])] + lane_h[lane_of(f["to"])] - 8,
                    lane_top[lane_of(f["from"])] + 8,
                    lane_top[lane_of(f["from"])] + lane_h[lane_of(f["from"])] - 8,
                ]
                outs = [A["x"] + A["w"] + STUB, col_x[cf] + col_w[cf] + gap / 2]
                ins = [Bx["x"] - STUB, col_x[ct] - gap / 2]
                tries = [
                    simplify([start, {"x": xo, "y": ca["y"]}, {"x": xo, "y": ch}, {"x": xi, "y": ch}, {"x": xi, "y": cb["y"]}, end])
                    for ch in channels
                    for xo in outs
                    for xi in ins
                ]
                found = next((t for t in tries if not through(t, [f["from"], f["to"]])), None)
                pts = found if found is not None else (search(f["from"], f["to"]) or tries[0])
        else:  # back (or into the same column): out of the bottom, along under the lane's content, into the bottom
            def legs(r: dict, c: float) -> list[float]:
                return [c, r["x"] + r["w"] - 10, r["x"] + 10, r["x"] + r["w"] * 3 / 4, r["x"] + r["w"] / 4]

            def build(xa: float, xb: float) -> list[dict]:
                base = max(A["y"] + A["h"], Bx["y"] + Bx["h"])
                lo, hi = min(xa, xb), max(xa, xb)
                moved = True
                while moved:
                    moved = False
                    for r in rect.values():
                        if r["x"] < hi and r["x"] + r["w"] > lo and r["y"] < base and r["y"] + r["h"] > base:
                            base = r["y"] + r["h"]
                            moved = True
                yb = base + 14 + (fi % 3) * 7
                return simplify([{"x": xa, "y": A["y"] + A["h"]}, {"x": xa, "y": yb}, {"x": xb, "y": yb}, {"x": xb, "y": Bx["y"] + Bx["h"]}])

            under = [build(xa, xb) for xa in legs(A, ca["x"]) for xb in legs(Bx, cb["x"])]
            below = Bx["y"] >= A["y"] + A["h"]
            above = Bx["y"] + Bx["h"] <= A["y"]
            # the other end is in another row (and neither end is a gateway, whose vertices carry its branches and its name): leave by the edge that
            # faces it and enter by the edge that faces back (from above, down into the top), along a channel just beside the target
            skip_faced_sided = (not below and not above) or _is_gate(kind_of[f["from"]]) or _is_gate(kind_of[f["to"]])
            faced: list[list[dict]] = []
            if not skip_faced_sided:
                for xa in legs(A, ca["x"]):
                    for xb in legs(Bx, cb["x"]):
                        ys = [Bx["y"] - 10, Bx["y"] - 20, lane_top[lane_of(f["to"])] + 6] if below else [Bx["y"] + Bx["h"] + 10, Bx["y"] + Bx["h"] + 20, lane_top[lane_of(f["to"])] + lane_h[lane_of(f["to"])] - 6]
                        for ych in ys:
                            faced.append(
                                simplify(
                                    [
                                        {"x": xa, "y": A["y"] + A["h"] if below else A["y"]},
                                        {"x": xa, "y": ych},
                                        {"x": xb, "y": ych},
                                        {"x": xb, "y": Bx["y"] if below else Bx["y"] + Bx["h"]},
                                    ]
                                )
                            )
            # last resort (a node stands right under and over the source, so no leg can leave by its top or bottom): leave by its side into
            # the gap between columns, run along the target's edge, enter from above / below
            cf = col_of(f["from"])
            gap_x = [col_x[cf] + col_w[cf] + gap / 2, col_x[cf] - gap / 2]
            sided: list[list[dict]] = []
            if not skip_faced_sided:
                for side, gx in enumerate(gap_x):
                    for xb in legs(Bx, cb["x"]):
                        ys = [Bx["y"] - 10, Bx["y"] - 20] if below else [Bx["y"] + Bx["h"] + 10, Bx["y"] + Bx["h"] + 20]
                        for ych in ys:
                            sided.append(
                                simplify(
                                    [
                                        {"x": A["x"] if side else A["x"] + A["w"], "y": ca["y"]},
                                        {"x": gx, "y": ca["y"]},
                                        {"x": gx, "y": ych},
                                        {"x": xb, "y": ych},
                                        {"x": xb, "y": Bx["y"] if below else Bx["y"] + Bx["h"]},
                                    ]
                                )
                            )
            tries = [*faced, *under, *sided]
            found = next((t for t in tries if not through(t, [f["from"], f["to"]])), None)
            pts = found if found is not None else (search(f["from"], f["to"]) or tries[0])
        out["edges"].append({"from": f["from"], "to": f["to"], "line": line, "points": pts})
        own = len(out["edges"]) - 1
        if f.get("label"):
            p0, p1, pn = pts[0], pts[1], pts[-1]
            lw = math.ceil(text_width(width_of, f["label"], S, 400)) + 2 * CHIP_PAD
            horiz = p0["y"] == p1["y"]
            self_loop = f["from"] == f["to"]
            # a condition belongs at the start of the flow, beside its first run; then anywhere beside the flow, nearest first
            if self_loop:
                near = [{"x": A["x"] + A["w"] + 26 + lw / 2, "y": ca["y"]}, {"x": A["x"] + A["w"] + 26 + lw / 2, "y": ca["y"] - 24}]
            elif horiz:
                near = [
                    {"x": p0["x"] + 8 + (abs(p1["x"] - p0["x"]) - 8) / 2, "y": p0["y"] - 14},
                    {"x": (p0["x"] + pn["x"]) / 2, "y": p0["y"] - 14},
                    {"x": p0["x"] + 8 + (abs(p1["x"] - p0["x"]) - 8) / 2, "y": p0["y"] + 14},
                ]
            else:
                off = 18 if p1["y"] > p0["y"] else -18
                near = [
                    {"x": p0["x"] + 40, "y": p0["y"] + off},
                    {"x": p0["x"] - 40, "y": p0["y"] + off},
                    {"x": p0["x"] + 30, "y": (p0["y"] + p1["y"]) / 2},
                ]
            more: list[dict] = []
            for i in range(len(pts) - 1):
                p, q = pts[i], pts[i + 1]
                mid = {"x": (p["x"] + q["x"]) / 2, "y": (p["y"] + q["y"]) / 2}
                for ox, oy in ((0, -16), (0, 16), (lw / 2 + 8, 0), (-(lw / 2 + 8), 0), (lw / 2 + 8, -16), (-(lw / 2 + 8), 16)):
                    more.append({"x": mid["x"] + ox, "y": mid["y"] + oy})
            pending.append((own, f["label"], [*near, *more]))

    # chips are white: one on another flow would cut it, so each keeps off every flow but its own, off the nodes and the other chips
    def chip(own: int, text: str, cands: list[dict]) -> None:
        lw = math.ceil(text_width(width_of, text, S, 400)) + 2 * CHIP_PAD
        lh = S + 8

        def box(c: dict) -> dict:
            return {"x": c["x"] - lw / 2, "y": c["y"] - lh / 2, "w": lw, "h": lh}

        def cost(b: dict) -> int:
            c = sum(1 for o in out["labels"] if hit(b, o))
            c += sum(1 for r in rect.values() if hit(b, r))
            c += sum(1 for o in out["labelBoxes"] if hit(b, o) and id(o) not in label_of_node)
            for k, e in enumerate(out["edges"]):
                if k == own:
                    continue
                pts_e = e["points"]
                if any(hit(b, seg_box(pts_e[i], pts_e[i + 1])) for i in range(len(pts_e) - 1)):
                    c += 1
            c += 0 if (b["x"] >= x + label_col and b["x"] + b["w"] <= x + width) else 5
            return c

        # the listed places first; when all are taken (a chip wider than the gap between two shapes), further above / below and beside, then the least crowded one
        wider = [{"x": p["x"] + ox, "y": p["y"] + oy} for p in cands for ox, oy in ((0, -lh), (0, lh), (0, -2 * lh), (0, 2 * lh), (lw / 2 + 10, 0), (-(lw / 2 + 10), 0), (lw / 2 + 10, -lh), (-(lw / 2 + 10), lh))]
        all_cands = [*cands, *wider]
        best = next((p for p in all_cands if cost(box(p)) == 0), None)
        if best is None:
            best = all_cands[0]
            for p in all_cands[1:]:
                if cost(box(p)) < cost(box(best)):
                    best = p
        b = box(best)
        out["labels"].append({"text": text, **b, "tx": best["x"], "ty": b["y"] + S + 2, "size": S, "edge": own})
        out["labelBoxes"].append({"label": text, **b})

    for own, text, cands in pending:
        chip(own, text, cands)

    # a gateway's label: above or below, to the left or right of its vertex, in the first spot clear of nodes, flows, chips and the lane names
    for n in band["nodes"]:
        m, r = meas[n["id"]], rect[n["id"]]
        if not _is_gate(kind_of[n["id"]]) or not m["label"]:
            continue
        lh = line_h(B)
        bh = len(m["label"]) * lh
        bw = max(math.ceil(text_width(width_of, ln, B, 400)) for ln in m["label"])
        cx = r["x"] + r["w"] / 2
        spots = [
            {"x": cx - bw, "y": r["y"] - 4 - bh, "a": "end"},
            {"x": cx, "y": r["y"] - 4 - bh, "a": "start"},
            {"x": cx - bw, "y": r["y"] + r["h"] + 4, "a": "end"},
            {"x": cx, "y": r["y"] + r["h"] + 4, "a": "start"},
        ]

        def free(s: dict) -> bool:
            b = {"x": s["x"], "y": s["y"], "w": bw, "h": bh}
            if not (s["x"] >= x + label_col + 2 and s["x"] + bw <= x + width and s["y"] >= y and s["y"] + bh <= y + out["h"]):
                return False
            if any(hit(b, q) for q in rect.values()):
                return False
            if any(hit(b, q) for q in out["labels"]):
                return False
            if any(hit(b, q) and id(q) not in label_of_node for q in out["labelBoxes"]):
                return False
            for e in out["edges"]:
                pts_e = e["points"]
                if any(hit(b, seg_box(pts_e[i], pts_e[i + 1])) for i in range(len(pts_e) - 1)):
                    return False
            return True

        # a flow that leaves the top / bottom vertex runs up / down the line at cx: when every spot touches it, stand 5px clear of it
        clear = [{**q, "x": (q["x"] - 5 if q["a"] == "end" else q["x"] + 5)} for q in spots]
        # still none: beside the diamond's side vertices, then further above / below; if even those are taken, the least crowded
        far = [
            {"x": r["x"] - 6 - bw, "y": r["y"] + r["h"] / 2 - bh - 2, "a": "end"},
            {"x": r["x"] + r["w"] + 6, "y": r["y"] + r["h"] / 2 - bh - 2, "a": "start"},
            {"x": r["x"] - 6 - bw, "y": r["y"] + r["h"] / 2 + 2, "a": "end"},
            {"x": r["x"] + r["w"] + 6, "y": r["y"] + r["h"] / 2 + 2, "a": "start"},
        ]
        for lvl in (1, 2):
            for sg in (-1, 1):
                for q in clear:
                    yy = (r["y"] - 4 - bh - lvl * lh) if sg < 0 else (r["y"] + r["h"] + 4 + lvl * lh)
                    far.append({**q, "y": yy})

        def crowd(q: dict) -> int:
            b = {"x": q["x"], "y": q["y"], "w": bw, "h": bh}
            c = 0 if (q["x"] >= x + label_col + 2 and q["x"] + bw <= x + width and q["y"] >= y and q["y"] + bh <= y + out["h"]) else 5
            c += sum(1 for o in rect.values() if hit(b, o))
            c += sum(1 for o in out["labels"] if hit(b, o))
            c += sum(1 for o in out["labelBoxes"] if hit(b, o) and id(o) not in label_of_node)
            for e in out["edges"]:
                pts_e = e["points"]
                if any(hit(b, seg_box(pts_e[i], pts_e[i + 1])) for i in range(len(pts_e) - 1)):
                    c += 1
            return c

        more = [*spots, *clear, *far]
        s = next((q for q in spots if free(q)), None)
        if s is None:
            s = next((q for q in clear if free(q)), None)
        if s is None:
            s = next((q for q in far if free(q)), None)
        if s is None:
            s = more[0]
            for q in more[1:]:
                if crowd(q) < crowd(s):
                    s = q
        for i, ln in enumerate(m["label"]):
            tw = math.ceil(text_width(width_of, ln, B, 400))
            ty = s["y"] + i * lh + B
            anchor = s["a"]
            tx = s["x"] + bw if anchor == "end" else s["x"]
            out["texts"].append({"text": ln, "x": tx, "y": ty, "size": B, "bold": False, "muted": False, "anchor": anchor})
            bx = s["x"] + bw - tw if anchor == "end" else s["x"]
            out["labelBoxes"].append({"label": ln, "x": bx, "y": ty - B, "w": tw, "h": B + 4})
    return out


def render_bpmn(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:444-478 renderBpmn(). NOT ported: `icons` (always empty — see the
    module docstring; the render loop over it in Node is therefore a no-op here and omitted)."""
    out: list[str] = []
    dim = bool(b.get("dim"))
    ink = PALETTE["muted"] if dim else PALETTE["text"]
    bg = PALETTE["bg"]
    for l in b["lanes"]:
        fill = bg if l["tone"] == "plain" else resolve_box_style(l["tone"], day)["fill"]
        out.append(f'<rect x="{snap4(l["x"])}" y="{snap4(l["y"])}" width="{snap4(l["w"])}" height="{snap4(l["h"])}" fill="{fill}" stroke="{PALETTE["muted"]}" stroke-width="2"/>')
        out.append(f'<rect x="{snap4(l["x"])}" y="{snap4(l["y"])}" width="{js_num(l["labelW"])}" height="{snap4(l["h"])}" fill="{PALETTE["code"]}" stroke="{PALETTE["muted"]}" stroke-width="2"/>')
    for e in b["edges"]:
        pts = list(e["points"])
        n = len(pts)
        tip, prev = pts[n - 1], pts[n - 2]
        dx, dy = _sign(tip["x"] - prev["x"]), _sign(tip["y"] - prev["y"])
        arrow_l, arrow_w = 11, 4.5
        pts[n - 1] = {"x": tip["x"] - dx * (arrow_l - 2), "y": tip["y"] - dy * (arrow_l - 2)}
        path_pts = " L".join(f"{snap4(p['x'])},{snap4(p['y'])}" for p in pts)
        dash = ' stroke-dasharray="6,4"' if e["line"] == "dashed" else ""
        head = f'M{snap4(tip["x"])},{snap4(tip["y"])} L{snap4(tip["x"] - dx * arrow_l - dy * arrow_w)},{snap4(tip["y"] - dy * arrow_l + dx * arrow_w)} L{snap4(tip["x"] - dx * arrow_l + dy * arrow_w)},{snap4(tip["y"] - dy * arrow_l - dx * arrow_w)} z'
        out.append(f'<path d="M{path_pts}" fill="none" stroke="{ink}" stroke-width="2"{dash}/>\n  <path d="{head}" fill="{ink}"/>')
    for nd in b["nodes"]:
        cx, cy = nd["x"] + nd["w"] / 2, nd["y"] + nd["h"] / 2
        style = resolve_box_style(nd["tone"], day)
        st = PALETTE["muted"] if dim else style["stroke"]
        fill = bg if dim else style["fill"]
        if nd["kind"] == "task":
            out.append(render_box_rect(x=nd["x"], y=nd["y"], w=nd["w"], h=nd["h"], tone=nd["tone"], dim=dim, day=day, default_tone="plain"))
            continue
        if nd["kind"] in ("start", "end"):
            sw = 5 if nd["kind"] == "end" else 2
            out.append(f'<circle cx="{snap4(cx)}" cy="{snap4(cy)}" r="{js_num(nd["w"] / 2 - 2)}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')
            continue
        r = nd["w"] / 2
        out.append(f'<path d="M{snap4(cx)},{snap4(nd["y"])} L{snap4(nd["x"] + nd["w"])},{snap4(cy)} L{snap4(cx)},{snap4(nd["y"] + nd["h"])} L{snap4(nd["x"])},{snap4(cy)} z" fill="{fill}" stroke="{st}" stroke-width="2"/>')
        m = r * 0.42
        if nd["kind"] == "xor":
            out.append(f'<path d="M{snap4(cx - m)},{snap4(cy - m)} L{snap4(cx + m)},{snap4(cy + m)} M{snap4(cx + m)},{snap4(cy - m)} L{snap4(cx - m)},{snap4(cy + m)}" fill="none" stroke="{st}" stroke-width="3"/>')
        elif nd["kind"] == "and":
            out.append(f'<path d="M{snap4(cx - m * 1.15)},{snap4(cy)} H{snap4(cx + m * 1.15)} M{snap4(cx)},{snap4(cy - m * 1.15)} V{snap4(cy + m * 1.15)}" fill="none" stroke="{st}" stroke-width="3"/>')
        else:
            out.append(f'<circle cx="{snap4(cx)}" cy="{snap4(cy)}" r="{snap4(m * 1.2)}" fill="none" stroke="{st}" stroke-width="3"/>')
    for t in b["texts"]:
        n = next((r for r in b["nodes"] if r["kind"] == "task" and t["x"] >= r["x"] and t["x"] <= r["x"] + r["w"] and t["y"] > r["y"] and t["y"] <= r["y"] + r["h"]), None)
        anchor = ' text-anchor="middle"' if t["anchor"] == "middle" else (' text-anchor="end"' if t["anchor"] == "end" else "")
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
