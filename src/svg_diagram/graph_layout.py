"""1:1 port of lib/graph-layout.ts's layoutTree()/layoutBalanced() — pure graph layout with
NO text/font dependency at all (callers pre-measure each node's {w, h}; these functions only
place already-sized boxes). Both are exported in Node and golden-tested live.

Golden master: lib/graph-layout.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

GAP, LEVEL_GAP = 24, 40


def _dup_check(seen: set[str], node_id: str) -> None:
    if node_id in seen:
        raise ValueError(f'graph layout: duplicate node id "{node_id}"')
    seen.add(node_id)


def layout_tree(root: dict, dir: str = "down", gap: float = GAP, level_gap: float = LEVEL_GAP) -> dict:
    """lib/graph-layout.ts:37-86 layoutTree(). `root`: {id, size: {w, h}, children?: [...]}."""

    def across(size: dict) -> float:
        return size["w"] if dir == "down" else size["h"]

    def along(size: dict) -> float:
        return size["h"] if dir == "down" else size["w"]

    seen: set[str] = set()
    level_depth: list[float] = []
    span: dict[int, float] = {}

    def measure(n: dict, level: int) -> float:
        _dup_check(seen, n["id"])
        while len(level_depth) <= level:
            level_depth.append(0)
        level_depth[level] = max(level_depth[level], along(n["size"]))
        kids = n.get("children") or []
        kids_span = 0.0
        for i, k in enumerate(kids):
            kids_span += measure(k, level + 1) + (gap if i else 0)
        mine = max(across(n["size"]), kids_span)
        span[id(n)] = mine
        return mine

    measure(root, 0)
    level_at: list[float] = []
    at = 0.0
    for d in level_depth:
        level_at.append(at)
        at += d + level_gap

    centres: dict[str, float] = {}
    levels: dict[str, int] = {}

    def place(n: dict, from_: float, level: int) -> None:
        mine = span[id(n)]
        kids = n.get("children") or []
        centres[n["id"]] = from_ + mine / 2
        levels[n["id"]] = level
        kids_span = 0.0
        for i, k in enumerate(kids):
            kids_span += span[id(k)] + (gap if i else 0)
        at = from_ + (mine - kids_span) / 2
        for k in kids:
            place(k, at, level + 1)
            at += span[id(k)] + gap

    place(root, 0, 0)
    nodes: dict[str, dict] = {}

    def index(n: dict) -> None:
        c, lvl = centres[n["id"]], levels[n["id"]]
        if dir == "down":
            nodes[n["id"]] = {"x": c - n["size"]["w"] / 2, "y": level_at[lvl], **n["size"]}
        else:
            nodes[n["id"]] = {"x": level_at[lvl], "y": c - n["size"]["h"] / 2, **n["size"]}
        for k in n.get("children") or []:
            index(k)

    index(root)
    edges: list[dict] = []

    def link(n: dict) -> None:
        p = nodes[n["id"]]
        for k in n.get("children") or []:
            q = nodes[k["id"]]
            if dir == "down":
                a, b = {"x": p["x"] + p["w"] / 2, "y": p["y"] + p["h"]}, {"x": q["x"] + q["w"] / 2, "y": q["y"]}
                mid = (a["y"] + b["y"]) / 2
                points = [a, {"x": a["x"], "y": mid}, {"x": b["x"], "y": mid}, b]
            else:
                a, b = {"x": p["x"] + p["w"], "y": p["y"] + p["h"] / 2}, {"x": q["x"], "y": q["y"] + q["h"] / 2}
                mid = (a["x"] + b["x"]) / 2
                points = [a, {"x": mid, "y": a["y"]}, {"x": mid, "y": b["y"]}, b]
            edges.append({"from": n["id"], "to": k["id"], "points": points})
            link(k)

    link(root)
    total = span[id(root)]
    depth = level_at[-1] + level_depth[-1]
    return {"nodes": nodes, "edges": edges, "w": total if dir == "down" else depth, "h": depth if dir == "down" else total}


def layout_balanced(root: dict, gap: float = GAP, level_gap: float = LEVEL_GAP, sides: dict[str, str] | None = None) -> dict:
    """lib/graph-layout.ts:92-146 layoutBalanced(): a mindmap's radial split."""
    sides = sides or {}
    kids = root.get("children") or []

    def height_of(k: dict) -> float:
        return layout_tree(k, dir="right", gap=gap, level_gap=level_gap)["h"]

    heights = [height_of(k) for k in kids]
    side = [sides.get(k["id"], "right") for k in kids]
    load = {"left": 0.0, "right": 0.0}
    for i, k in enumerate(kids):
        if sides.get(k["id"]):
            load[side[i]] += heights[i]
    free = [i for i, k in enumerate(kids) if not sides.get(k["id"])]
    free_total = sum(heights[i] for i in free)
    acc = 0.0
    for i in free:
        mid = acc + heights[i] / 2
        side[i] = "right" if load["right"] + mid <= (load["left"] + load["right"] + free_total) / 2 else "left"
        acc += heights[i]

    def half(which: str) -> dict | None:
        ks = [k for i, k in enumerate(kids) if side[i] == which]
        if not ks:
            return None
        return layout_tree({"id": f"{root['id']}\x00{which}", "size": {"w": 0, "h": 0}, "children": ks}, dir="right", gap=gap, level_gap=level_gap)

    right, left = half("right"), half("left")
    right_w = right["w"] - level_gap if right else 0
    left_w = left["w"] - level_gap if left else 0
    height = max(right["h"] if right else 0, left["h"] if left else 0, root["size"]["h"])
    root_x = left_w + (level_gap if left else 0)
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen = {root["id"]}
    nodes[root["id"]] = {"x": root_x, "y": (height - root["size"]["h"]) / 2, **root["size"]}
    root_p = nodes[root["id"]]

    def take(t: dict | None, which: str) -> None:
        if t is None:
            return
        ghost = f"{root['id']}\x00{which}"
        dy = (height - t["h"]) / 2
        shift_x = root_x + root["size"]["w"] if which == "right" else 0
        for node_id, p in t["nodes"].items():
            if node_id == ghost:
                continue
            _dup_check(seen, node_id)
            x = p["x"] + shift_x if which == "right" else t["w"] - p["x"] - p["w"]
            nodes[node_id] = {**p, "x": x, "y": p["y"] + dy}

        def root_edge(to: str) -> list[dict]:
            q = nodes[to]
            a = {"x": root_p["x"] + root_p["w"] if which == "right" else root_p["x"], "y": root_p["y"] + root_p["h"] / 2}
            b = {"x": q["x"] if which == "right" else q["x"] + q["w"], "y": q["y"] + q["h"] / 2}
            m = (a["x"] + b["x"]) / 2
            return [a, {"x": m, "y": a["y"]}, {"x": m, "y": b["y"]}, b]

        for e in t["edges"]:
            if e["from"] == ghost:
                edges.append({"from": root["id"], "to": e["to"], "points": root_edge(e["to"])})
                continue
            pts = [{"x": (p["x"] + shift_x if which == "right" else t["w"] - p["x"]), "y": p["y"] + dy} for p in e["points"]]
            edges.append({"from": e["from"], "to": e["to"], "points": pts})

    take(right, "right")
    take(left, "left")
    w = left_w + (level_gap if left else 0) + root["size"]["w"] + (level_gap if right else 0) + right_w
    return {"nodes": nodes, "edges": edges, "w": w, "h": height}
