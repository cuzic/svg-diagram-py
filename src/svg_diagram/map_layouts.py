"""1:1 port of lib/map-layouts.ts — mindmap() layouts besides the radial one (layoutBalanced,
in graph_layout.py): mirror, org/outline (hanging lists), brace map, fishbone, timeline. Pure,
like graph_layout.py: sizes in, rectangles and edge polylines out. All exported in Node,
golden-tested live.

Golden master: lib/map-layouts.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

GAP = 20


def _dup(seen: set[str], node_id: str) -> None:
    if node_id in seen:
        raise ValueError(f'graph layout: duplicate node id "{node_id}"')
    seen.add(node_id)


def mirror(t: dict, axis: str) -> dict:
    """lib/map-layouts.ts:15-20 mirror()."""

    def fx(p: dict) -> dict:
        return {"x": t["w"] - p["x"], "y": p["y"]} if axis == "x" else {"x": p["x"], "y": t["h"] - p["y"]}

    nodes = {}
    for node_id, p in t["nodes"].items():
        nodes[node_id] = {**p, "x": t["w"] - p["x"] - p["w"]} if axis == "x" else {**p, "y": t["h"] - p["y"] - p["h"]}
    edges = [{**e, "points": [fx(p) for p in e["points"]]} for e in t["edges"]]
    out = {**t, "nodes": nodes, "edges": edges}
    if t.get("braces"):
        if axis == "x":
            out["braces"] = [{**b, "x": t["w"] - b["x"], "tipX": t["w"] - b["tipX"], "side": "left"} for b in t["braces"]]
        else:
            out["braces"] = [{**b, "y1": t["h"] - b["y2"], "y2": t["h"] - b["y1"], "ymid": t["h"] - b["ymid"]} for b in t["braces"]]
    return out


def layout_hanging(root: dict, row_first: bool = False, gap: float = 12, indent: float = 28, row_gap: float = 28) -> dict:
    """lib/map-layouts.ts:27-71 layoutHanging()."""
    seen: set[str] = set()
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def lst(n: dict, x: float, y: float) -> dict:
        _dup(seen, n["id"])
        nodes[n["id"]] = {"x": x, "y": y, **n["size"]}
        bottom, right = y + n["size"]["h"], x + n["size"]["w"]
        for c in n.get("children") or []:
            top, cx = bottom + gap, x + indent
            r = lst(c, cx, top)
            cy = top + c["size"]["h"] / 2
            edges.append({"from": n["id"], "to": c["id"], "points": [{"x": x + 14, "y": y + n["size"]["h"]}, {"x": x + 14, "y": cy}, {"x": cx, "y": cy}]})
            bottom, right = r["bottom"], max(right, r["right"])
        return {"bottom": bottom, "right": right}

    if not row_first:
        r = lst(root, 0, 0)
        return {"nodes": nodes, "edges": edges, "w": r["right"], "h": r["bottom"]}

    kids = root.get("children") or []
    _dup(seen, root["id"])
    row_top = root["size"]["h"] + 44
    cx = 0.0
    h = row_top
    cols: list[dict] = []
    for k in kids:
        r = lst(k, cx, row_top)
        cols.append({"id": k["id"], "x": cx, "w": k["size"]["w"]})
        h = max(h, r["bottom"])
        cx = r["right"] + row_gap
    w = max(cx - row_gap if kids else 0, root["size"]["w"])
    first, last = (cols[0], cols[-1]) if cols else (None, None)
    root_x = (first["x"] + first["w"] / 2 + last["x"] + last["w"] / 2) / 2 - root["size"]["w"] / 2 if first and last else 0.0
    shift = max(0.0, -root_x)
    if shift:
        for node_id, p in list(nodes.items()):
            nodes[node_id] = {**p, "x": p["x"] + shift}
        for e in edges:
            e["points"] = [{"x": p["x"] + shift, "y": p["y"]} for p in e["points"]]
        for c in cols:
            c["x"] += shift
    nodes[root["id"]] = {"x": root_x + shift, "y": 0, **root["size"]}
    bus = root["size"]["h"] + 22
    rcx = root_x + shift + root["size"]["w"] / 2
    root_l, root_r = root_x + shift + 8, root_x + shift + root["size"]["w"] - 8
    for c in cols:
        ccx = c["x"] + c["w"] / 2
        if ccx != rcx and abs(ccx - rcx) <= 4 and root_l <= ccx <= root_r:
            edges.append({"from": root["id"], "to": c["id"], "points": [{"x": ccx, "y": root["size"]["h"]}, {"x": ccx, "y": row_top}]})
            continue
        edges.append({"from": root["id"], "to": c["id"], "points": [{"x": rcx, "y": root["size"]["h"]}, {"x": rcx, "y": bus}, {"x": ccx, "y": bus}, {"x": ccx, "y": row_top}]})
    return {"nodes": nodes, "edges": edges, "w": max(w + shift, root_x + shift + root["size"]["w"]), "h": h}


def layout_brace(root: dict, gap: float = GAP) -> dict:
    """lib/map-layouts.ts:74-94 layoutBrace()."""
    from .graph_layout import layout_tree

    t = layout_tree(root, dir="right", gap=gap, level_gap=64)
    braces: list[dict] = []
    edges: list[dict] = []

    def walk(n: dict) -> None:
        p = t["nodes"][n["id"]]
        kids = [{"c": c, "p": t["nodes"][c["id"]]} for c in n.get("children") or []]
        if not kids:
            return
        if len(kids) == 1:
            k = kids[0]
            cy = k["p"]["y"] + k["p"]["h"] / 2
            edges.append({"from": n["id"], "to": k["c"]["id"], "points": [{"x": p["x"] + p["w"], "y": p["y"] + p["h"] / 2}, {"x": k["p"]["x"], "y": cy}]})
            walk(k["c"])
            return
        left = min(k["p"]["x"] for k in kids)
        spine = left - 26
        y1 = min(k["p"]["y"] + k["p"]["h"] / 2 for k in kids)
        y2 = max(k["p"]["y"] + k["p"]["h"] / 2 for k in kids)
        ymid = p["y"] + p["h"] / 2
        braces.append({"x": spine, "y1": y1, "y2": y2, "ymid": ymid, "tipX": spine - 10, "side": "right"})
        edges.append({"from": n["id"], "to": n["id"], "points": [{"x": p["x"] + p["w"], "y": ymid}, {"x": spine - 10, "y": ymid}]})
        for k in kids:
            edges.append({"from": n["id"], "to": k["c"]["id"], "points": [{"x": spine + 8, "y": k["p"]["y"] + k["p"]["h"] / 2}, {"x": k["p"]["x"], "y": k["p"]["y"] + k["p"]["h"] / 2}]})
            walk(k["c"])

    walk(root)
    return {"nodes": t["nodes"], "edges": edges, "braces": braces, "w": t["w"], "h": t["h"]}


def layout_fishbone(root: dict, gap: float = 8) -> dict:
    """lib/map-layouts.ts:102-150 layoutFishbone()."""
    seen = {root["id"]}
    cats = root.get("children") or []
    for c in cats:
        _dup(seen, c["id"])
    lists: dict[str, dict] = {}
    for c in cats:
        for k in c.get("children") or []:
            l = layout_hanging(k, gap=6, indent=20)
            for node_id in l["nodes"]:
                _dup(seen, node_id)
            lists[k["id"]] = mirror(l, "x")

    def blocks_h(c: dict) -> float:
        total = 0.0
        for i, k in enumerate(c.get("children") or []):
            total += lists[k["id"]]["h"] + (gap if i else 0)
        return total

    def length_of(c: dict) -> float:
        return 16 + blocks_h(c) + 22

    half = max([0.0] + [c["size"]["h"] + length_of(c) for c in cats] + [root["size"]["h"] / 2])
    spine_y = half

    def cause_w(c: dict) -> float:
        kids = c.get("children") or []
        return max([0.0] + [lists[k["id"]]["w"] for k in kids])

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    rows: list[list[dict]] = [[], []]
    for i, c in enumerate(cats):
        rows[i % 2].append(c)
    spine_end = 120.0
    for ri, row in enumerate(rows):
        top = ri == 0
        cursor = 0.0 if top else 56.0
        for c in row:
            cat_y = 0.0 if top else 2 * half - c["size"]["h"]
            start_y = cat_y + c["size"]["h"] if top else cat_y
            direction = 1 if top else -1
            run = abs(spine_y - start_y)
            dxs = run * 0.4
            bx = cursor + max(cause_w(c) + 12, c["size"]["w"] / 2)
            nodes[c["id"]] = {"x": bx - c["size"]["w"] / 2, "y": cat_y, **c["size"]}
            edges.append({"from": c["id"], "to": c["id"], "points": [{"x": bx, "y": start_y}, {"x": bx + dxs, "y": spine_y}]})
            y = start_y + direction * 16
            for k in c.get("children") or []:
                raw = lists[k["id"]]
                block = raw if top else mirror(raw, "y")
                y0 = y if top else y - block["h"]
                kp = block["nodes"][k["id"]]
                cyk = y0 + kp["y"] + kp["h"] / 2
                bxk = bx + dxs * (abs(cyk - start_y) / run)
                sx = bxk - 12 - block["w"]
                for node_id, p in block["nodes"].items():
                    nodes[node_id] = {**p, "x": p["x"] + sx, "y": p["y"] + y0}
                for e in block["edges"]:
                    edges.append({**e, "points": [{"x": q["x"] + sx, "y": q["y"] + y0} for q in e["points"]]})
                edges.append({"from": c["id"], "to": k["id"], "points": [{"x": bxk - 12, "y": cyk}, {"x": bxk, "y": cyk}]})
                y += direction * (block["h"] + gap)
            cursor = max(bx + c["size"]["w"] / 2, bx + dxs) + 28
            spine_end = max(spine_end, bx + dxs + 24)
    rx = spine_end + 16
    nodes[root["id"]] = {"x": rx, "y": spine_y - root["size"]["h"] / 2, **root["size"]}
    edges.insert(0, {"from": root["id"], "to": root["id"], "points": [{"x": 0, "y": spine_y}, {"x": rx, "y": spine_y}], "bold": True})
    min_x = min([0.0] + [p["x"] for p in nodes.values()])
    if min_x < 0:
        for node_id, p in list(nodes.items()):
            nodes[node_id] = {**p, "x": p["x"] - min_x}
        for e in edges:
            e["points"] = [{"x": p["x"] - min_x, "y": p["y"]} for p in e["points"]]
    return {"nodes": nodes, "edges": edges, "w": rx - min_x + root["size"]["w"], "h": 2 * half}


def layout_timeline_map(root: dict, gap: float = 28) -> dict:
    """lib/map-layouts.ts:156-181 layoutTimelineMap()."""
    seen = {root["id"]}
    kids = root.get("children") or []
    lists = []
    for k in kids:
        sub = layout_hanging(k, gap=10, indent=24)
        for node_id in sub["nodes"]:
            _dup(seen, node_id)
        lists.append(sub)
    above = max([0.0] + [l["h"] for i, l in enumerate(lists) if i % 2 == 0])
    below = max([0.0] + [l["h"] for i, l in enumerate(lists) if i % 2 == 1])
    stub = 26
    axis_y = max(above + stub, root["size"]["h"] / 2)
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    nodes[root["id"]] = {"x": 0, "y": axis_y - root["size"]["h"] / 2, **root["size"]}
    cx = root["size"]["w"] + 36
    for i, k in enumerate(kids):
        sub = lists[i]
        up = i % 2 == 0
        x = cx
        dy = axis_y - stub - sub["h"] if up else axis_y + stub
        placed = mirror(sub, "y") if up else sub
        for node_id, p in placed["nodes"].items():
            nodes[node_id] = {**p, "x": p["x"] + x, "y": p["y"] + dy}
        for e in placed["edges"]:
            edges.append({"from": e["from"], "to": e["to"], "points": [{"x": p["x"] + x, "y": p["y"] + dy} for p in e["points"]]})
        kp = nodes[k["id"]]
        stem_x = kp["x"] + kp["w"] / 2
        edges.append({"from": root["id"], "to": k["id"], "points": [{"x": stem_x, "y": axis_y}, {"x": stem_x, "y": kp["y"] + kp["h"] if up else kp["y"]}]})
        cx += sub["w"] + gap
    end_x = max(cx - gap, root["size"]["w"])
    edges.insert(0, {"from": root["id"], "to": root["id"], "points": [{"x": root["size"]["w"], "y": axis_y}, {"x": end_x, "y": axis_y}], "bold": True})
    return {"nodes": nodes, "edges": edges, "w": end_x, "h": axis_y + max(below + stub, root["size"]["h"] / 2)}
