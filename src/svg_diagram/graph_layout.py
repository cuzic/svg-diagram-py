"""1:1 port of lib/graph-layout.ts's layoutTree()/layoutBalanced()/layoutLayered()/breakCycles() —
pure graph layout with NO text/font dependency at all (callers pre-measure each node's {w, h});
these functions only place already-sized boxes. All exported in Node and golden-tested live.

layoutLayered() is the shared "layered routing" engine behind states()/classes()/bpmn()/cause()/
pert()/causalLoop()/dependencyNetwork() (see py/BANDS.md's Tier 3 note) — longest-path layering,
barycentre crossing reduction, and either relaxation or Brandes-Köpf coordinate assignment. Porting
it does not by itself unlock any of those bands (each still needs its own caller-side code, and
states/classes/cause/pert/causalLoop/dependencyNetwork go through lib/layered-route.ts's
layeredAttempt wrapper — hop/retry logic on top of this — which is NOT ported yet), but it is the
single largest reusable piece of that investment.

Golden master: lib/graph-layout.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
from collections.abc import Callable

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


def break_cycles(
    nodes: list[dict], edges: list[dict], declared: list[int] | None = None, start: list[str] | None = None
) -> set[int]:
    """lib/graph-layout.ts:185-242 breakCycles(). Returns the indices (into `edges`) of the
    edges a layering should treat as reversed to make the graph acyclic."""
    declared = declared or []
    start = start or []
    decl: set[int] = set()
    for i in declared:
        if not isinstance(i, int) or i < 0 or i >= len(edges):
            raise ValueError(f"graph layout: back edge index {i} is not one of the {len(edges)} edges")
        e = edges[i]
        if e["from"] != e["to"]:
            decl.add(i)

    def name(i: int) -> str:
        e = edges[i]
        return f"{e['from']} -> {e['to']}"

    rest: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for i, e in enumerate(edges):
        if e["from"] != e["to"] and i not in decl:
            rest[e["from"]].append(e["to"])

    def reach(from_: str, to: str, avoid: set[str] | None = None) -> bool:
        avoid = avoid or set()
        seen = {from_}
        todo = [from_]
        while todo:
            u = todo.pop()
            if u == to:
                return True
            for v in rest.get(u, []):
                if v not in seen and v not in avoid:
                    seen.add(v)
                    todo.append(v)
        return False

    lst = list(decl)
    budget = [20000]

    def two_on_one_cycle(d1: int, d2: int) -> bool:
        e1, e2 = edges[d1], edges[d2]
        goal = e2["from"]
        on_path: set[str] = set()

        def walk(u: str) -> bool:
            budget[0] -= 1
            if budget[0] < 0:
                return False
            on_path.add(u)
            found = False
            if u == goal:
                found = e2["to"] not in on_path and reach(e2["to"], e1["from"], on_path)
            else:
                for v in rest.get(u, []):
                    if v not in on_path and walk(v):
                        found = True
                        break
            on_path.discard(u)
            return found

        return walk(e1["to"])

    for idx, d1 in enumerate(lst):
        for d2 in lst[idx + 1 :]:
            if two_on_one_cycle(d1, d2):
                raise ValueError(
                    f"graph layout: back edges {name(d1)} and {name(d2)} are on one cycle. "
                    "One back edge cuts a cycle: keep back on the one edge that is the return in meaning"
                )

    for d in lst:
        e = edges[d]
        if not reach(e["to"], e["from"]):
            raise ValueError(
                f"graph layout: back edge {name(d)} closes no cycle: there is no way from "
                f"{e['to']} back to {e['from']} along the other edges. "
                "Mark only the edge that returns to the start of a loop"
            )

    state: dict[str, int] = {}
    back_pairs: set[str] = set()

    def dfs(u: str) -> None:
        state[u] = 1
        for v in rest[u]:
            if state.get(v) == 1:
                back_pairs.add(f"{u}\x00{v}")
            elif not state.get(v):
                dfs(v)
        state[u] = 2

    known = {n["id"] for n in nodes}
    for s in [s for s in start if s in known] + [n["id"] for n in nodes]:
        if not state.get(s):
            dfs(s)

    out = set(decl)
    for i, e in enumerate(edges):
        if e["from"] != e["to"] and i not in decl and f"{e['from']}\x00{e['to']}" in back_pairs:
            out.add(i)
    return out


def _brandes_koepf(
    rows: list[list[str]],
    succ: dict[str, list[str]],
    pred: dict[str, list[str]],
    width: Callable[[str], float],
    gap: float,
    dummy: Callable[[str], bool],
) -> dict[str, float]:
    """lib/graph-layout.ts:250-322 brandesKoepf()."""
    ids = [node_id for r in rows for node_id in r]
    layouts: list[dict[str, float]] = []
    for up in (False, True):
        for right in (False, True):
            view = [list(reversed(r)) if right else list(r) for r in (list(reversed(rows)) if up else rows)]
            prev = succ if up else pred
            pos: dict[str, int] = {}
            row_of: dict[str, list[str]] = {}
            for r in view:
                for i, node_id in enumerate(r):
                    pos[node_id] = i
                    row_of[node_id] = r

            def before(v: str) -> list[str]:
                return sorted(prev[v], key=lambda a: pos[a])

            conflict: set[str] = set()
            for i in range(len(view) - 1):
                high, low = view[i], view[i + 1]
                k0, l = 0, 0
                for l1, low_id in enumerate(low):
                    inner = next((u for u in prev[low_id] if dummy(u)), None) if dummy(low_id) else None
                    if l1 == len(low) - 1 or inner is not None:
                        k1 = pos[inner] if inner is not None else len(high) - 1
                        while l <= l1:
                            lid = low[l]
                            for u in prev[lid]:
                                k = pos[u]
                                if k < k0 or k > k1:
                                    conflict.add(f"{u}\x00{lid}")
                            l += 1
                        k0 = k1

            root = {node_id: node_id for node_id in ids}
            align = {node_id: node_id for node_id in ids}
            for r in view[1:]:
                last = -1
                for v in r:
                    ns = before(v)
                    d = len(ns)
                    if not d:
                        continue
                    medians = [ns[(d - 1) // 2]] if d % 2 else [ns[d // 2 - 1], ns[d // 2]]
                    for m in medians:
                        if align[v] == v and f"{m}\x00{v}" not in conflict and last < pos[m]:
                            align[m] = v
                            root[v] = root[m]
                            align[v] = root[v]
                            last = pos[m]

            sink = {node_id: node_id for node_id in ids}
            shift = {node_id: math.inf for node_id in ids}
            x: dict[str, float] = {}

            def place_block(v: str) -> None:
                if v in x:
                    return
                x[v] = 0.0
                w = v
                while True:
                    i = pos[w]
                    if i > 0:
                        p = row_of[w][i - 1]
                        u = root[p]
                        d = (width(p) + width(w)) / 2 + gap
                        place_block(u)
                        if sink[v] == v:
                            sink[v] = sink[u]
                        if sink[v] != sink[u]:
                            shift[sink[u]] = min(shift[sink[u]], x[v] - x[u] - d)
                        else:
                            x[v] = max(x[v], x[u] + d)
                    w = align[w]
                    if w == v:
                        break

            for node_id in ids:
                if root[node_id] == node_id:
                    place_block(node_id)
            out: dict[str, float] = {}
            for node_id in ids:
                rt = root[node_id]
                sh = shift[sink[rt]]
                out[node_id] = (x[rt] + (sh if sh < math.inf else 0)) * (-1 if right else 1)
            layouts.append(out)

    def lo(m: dict[str, float]) -> float:
        return min(m[node_id] - width(node_id) / 2 for node_id in ids)

    def hi(m: dict[str, float]) -> float:
        return max(m[node_id] + width(node_id) / 2 for node_id in ids)

    narrow = layouts[0]
    for m in layouts[1:]:
        if hi(m) - lo(m) < hi(narrow) - lo(narrow):
            narrow = m
    aligned: list[dict[str, float]] = []
    for k, m in enumerate(layouts):
        d = (lo(narrow) - lo(m)) if k % 2 == 0 else (hi(narrow) - hi(m))
        aligned.append({node_id: m[node_id] + d for node_id in ids})
    result: dict[str, float] = {}
    for node_id in ids:
        v = sorted(m[node_id] for m in aligned)
        result[node_id] = (v[1] + v[2]) / 2
    for r in rows:
        for i in range(1, len(r)):
            cur, prv = r[i], r[i - 1]
            result[cur] = max(result[cur], result[prv] + (width(prv) + width(cur)) / 2 + gap)
    return result


def layout_layered(nodes: list[dict], edges: list[dict], opts: dict | None = None) -> dict:
    """lib/graph-layout.ts:329-584 layoutLayered(). `nodes`: [{id, size: {w, h}}, ...].
    `edges`: [{from, to}, ...]. `opts`: dir/gap/levelGap/sweeps/tighten/alap/transpose/coord/
    outer/fold/start/back (see the TS interface LayeredOpts for the meaning of each)."""
    opts = opts or {}
    dir_ = opts.get("dir", "right")
    gap = opts.get("gap", GAP)
    level_gap = opts.get("levelGap", LEVEL_GAP * 1.5)
    sweeps = opts.get("sweeps", 4)

    ids: set[str] = set()
    for n in nodes:
        _dup_check(ids, n["id"])
    for e in edges:
        for node_id in (e["from"], e["to"]):
            if node_id not in ids:
                raise ValueError(f"graph layout: edge {e['from']} -> {e['to']} names unknown node \"{node_id}\"")
    order = {n["id"]: i for i, n in enumerate(nodes)}

    def across(s: dict) -> float:
        return s["w"] if dir_ == "down" else s["h"]

    def along(s: dict) -> float:
        return s["h"] if dir_ == "down" else s["w"]

    # 1. break cycles: edges declared as returns first, then a DFS over the others
    reversed_at = break_cycles(nodes, edges, opts.get("back") or [], opts.get("start"))
    starts = [s for s in (opts.get("start") or []) if s in ids]
    dag: list[dict] = []
    for index, e in enumerate(edges):
        if e["from"] == e["to"]:
            continue
        if index in reversed_at:
            dag.append({"a": e["to"], "b": e["from"], "e": e, "index": index, "rev": True})
        else:
            dag.append({"a": e["from"], "b": e["to"], "e": e, "index": index, "rev": False})

    # 2. longest-path layering (a start node stays on layer 0)
    layer: dict[str, int] = {}
    preds: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for d in dag:
        preds[d["b"]].append(d["a"])

    def depth(u: str, trail: set[str]) -> int:
        if u in layer:
            return layer[u]
        if u in starts and not preds[u]:
            layer[u] = 0
            return 0
        if u in trail:
            return 0
        trail.add(u)
        level = 0
        for p in preds[u]:
            level = max(level, depth(p, trail) + 1)
        trail.discard(u)
        layer[u] = level
        return level

    for n in nodes:
        depth(n["id"], set())

    if opts.get("tighten"):
        nearest: dict[str, float] = {}
        for d in dag:
            nearest[d["a"]] = min(nearest.get(d["a"], math.inf), layer[d["b"]])
        for u, l in nearest.items():
            if not preds[u] and u not in starts and l - 1 > layer[u]:
                layer[u] = int(l - 1)

    if opts.get("alap"):
        alap_keep = set(opts["alap"].get("keep") or []) | set(starts)
        movers: set[str] = set()
        succs: dict[str, list[str]] = {n["id"]: [] for n in nodes}
        for d in dag:
            succs[d["a"]].append(d["b"])
        by_layer = sorted(layer.keys(), key=lambda p: layer[p])
        for u in by_layer:
            if u not in alap_keep and all(p in movers for p in preds[u]):
                movers.add(u)
        for u in reversed(by_layer):
            ts = succs[u]
            if u not in movers or not ts:
                continue
            l = min(layer[t] for t in ts) - 1
            if l > layer[u]:
                layer[u] = l

    # 2b. fold: a layer wider than `fold` becomes rows, each its own layer (ADR 0010 D7)
    def fold_layers() -> list[dict]:
        limit = opts["fold"]
        n_old = max(layer.values(), default=-1) + 1
        back_decl = set(opts.get("back") or [])
        outer_opt = opts.get("outer")

        def outer_edge(d: dict) -> bool:
            return bool(outer_opt) and d["rev"] and abs(layer[d["b"]] - layer[d["a"]]) >= 2 and (
                outer_opt["which"] == "all" or d["index"] in back_decl
            )

        through = [d for d in dag if layer[d["a"]] != layer[d["b"]] and not outer_edge(d)]
        skips = [0] * n_old
        in_of: dict[str, int] = {}
        out_of: dict[str, int] = {}
        for d in through:
            for l in range(layer[d["a"]] + 1, layer[d["b"]]):
                skips[l] += 1
            out_of[d["a"]] = out_of.get(d["a"], 0) + 1
            in_of[d["b"]] = in_of.get(d["b"], 0) + 1

        members: list[list[dict]] = [[] for _ in range(n_old)]
        for n in nodes:
            members[layer[n["id"]]].append(n)

        def used(ns: list[dict], dummies: int) -> float:
            return sum(across(n["size"]) for n in ns) + gap * (max(0, len(ns) - 1) + dummies)

        rows_of: list[list[list[dict]]] = []
        cut: list[dict] = []
        for l, ns in enumerate(members):
            skip = skips[l]
            if len(ns) < 2 or used(ns, skip) <= limit:
                rows_of.append([ns])
                continue
            extra: list[float] = []
            rows: list[list[dict]] = [[]]
            for _round in range(len(ns) * 2 + 1):
                rows = [[]]
                for n in ns:
                    cur = rows[-1]
                    if cur and used([*cur, n], skip + (extra[len(rows) - 1] if len(rows) - 1 < len(extra) else 0)) > limit:
                        rows.append([n])
                    else:
                        cur.append(n)
                counted = [0.0] * len(rows)
                for k, r in enumerate(rows):
                    for n in r:
                        for j in range(k):
                            counted[j] += in_of.get(n["id"], 0)
                        for j in range(k + 1, len(rows)):
                            counted[j] += out_of.get(n["id"], 0)
                if all(len(r) < 2 or used(r, skip + counted[k]) <= limit for k, r in enumerate(rows)):
                    break
                extra = [max(counted[k], extra[k] if k < len(extra) else 0) for k in range(len(counted))]
            rows_of.append(rows)
            cut.append({"layer": l, "rows": len(rows)})

        if not cut:
            return cut
        base = 0
        for rows in rows_of:
            for k, r in enumerate(rows):
                for n in r:
                    layer[n["id"]] = base + k
            base += len(rows)
        return cut

    folded = fold_layers() if opts.get("fold") is not None else []

    # 3. dummies for edges that skip layers
    slots: dict[str, dict] = {n["id"]: {"id": n["id"], "real": True, "size": n["size"], "layer": layer[n["id"]]} for n in nodes}
    chains: list[dict] = []
    declared_set = set(opts.get("back") or [])
    succ: dict[str, list[str]] = {s: [] for s in slots}
    pred: dict[str, list[str]] = {s: [] for s in slots}

    def link(a: str, b: str) -> None:
        succ[a].append(b)
        pred[b].append(a)

    outer_opt = opts.get("outer")
    for i, d in enumerate(dag):
        la, lb = layer[d["a"]], layer[d["b"]]
        chain = [d["a"]]
        to = d["b"]
        step = 1 if lb >= la else -1
        if la == lb:
            chain.append(d["b"])
            chains.append({"e": d["e"], "index": d["index"], "ids": chain, "rev": d["rev"]})
            continue
        if outer_opt and d["rev"] and abs(lb - la) >= 2 and (outer_opt["which"] == "all" or d["index"] in declared_set):
            chains.append({"e": d["e"], "index": d["index"], "ids": [d["a"], d["b"]], "rev": True, "outer": True})
            continue
        l = la + step
        while l != lb:
            slot_id = f"\x00d{i}.{l}"
            slots[slot_id] = {"id": slot_id, "real": False, "size": {"w": 1, "h": 1}, "layer": l}
            succ[slot_id] = []
            pred[slot_id] = []
            chain.append(slot_id)
            l += step
        chain.append(to)
        chains.append({"e": d["e"], "index": d["index"], "ids": chain, "rev": d["rev"]})
        asc = chain if la < lb else list(reversed(chain))
        for k in range(len(asc) - 1):
            link(asc[k], asc[k + 1])

    n_layers = max((s["layer"] for s in slots.values()), default=-1) + 1

    def rank(node_id: str) -> float:
        return (1_000_000 + order.get(node_id, 0)) if node_id.startswith("\x00") else order.get(node_id, 0)

    parent: dict[str, str] = {k: k for k in slots}

    def find(a: str) -> str:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, bs in succ.items():
        for b in bs:
            parent[find(a)] = find(b)

    by_rank = sorted(slots.values(), key=lambda sl: (rank(sl["id"]), sl["id"]))
    comp_idx: dict[str, int] = {}
    comp_of_root: dict[str, int] = {}
    use_bk = opts.get("coord") == "bk"
    for sl in by_rank:
        r = find(sl["id"]) if use_bk else ""
        if r not in comp_of_root:
            comp_of_root[r] = len(comp_of_root)
        comp_idx[sl["id"]] = comp_of_root[r]
    n_comp = len(comp_of_root)

    rows: list[list[str]] = [[] for _ in range(n_layers)]
    for sl in sorted(by_rank, key=lambda sl: comp_idx[sl["id"]]):
        rows[sl["layer"]].append(sl["id"])

    # 4. barycentre sweeps, down then up, keeping the order of nodes with no neighbour
    pos: dict[str, int] = {}

    def reindex() -> None:
        for r in rows:
            for i, node_id in enumerate(r):
                pos[node_id] = i

    reindex()

    def sort_by(r: list[str], nb: dict[str, list[str]]) -> None:
        key: dict[str, float] = {}
        for i, node_id in enumerate(r):
            ns = nb[node_id]
            key[node_id] = (sum(pos[n] for n in ns) / len(ns)) if ns else i
        r.sort(key=lambda node_id: (comp_idx[node_id], key[node_id], pos[node_id]))
        for i, node_id in enumerate(r):
            pos[node_id] = i

    def crossings_at(l: int) -> int:
        ls: list[tuple[int, int]] = []
        for u in rows[l]:
            for v in succ[u]:
                ls.append((pos[u], pos[v]))
        c = 0
        for i, a in enumerate(ls):
            for b in ls[i + 1 :]:
                if (a[0] - b[0]) * (a[1] - b[1]) < 0:
                    c += 1
        return c

    def all_crossings() -> int:
        return sum(crossings_at(l) for l in range(n_layers - 1))

    best: dict | None = None
    if opts.get("transpose"):
        best = {"rows": [list(r) for r in rows], "cross": all_crossings()}
    for _s in range(sweeps):
        for l in range(1, n_layers):
            sort_by(rows[l], pred)
        for l in range(n_layers - 2, -1, -1):
            sort_by(rows[l], succ)
        if best is not None:
            c = all_crossings()
            if c < best["cross"]:
                best = {"rows": [list(r) for r in rows], "cross": c}
    if best is not None:
        for l, r in enumerate(best["rows"]):
            rows[l][:] = r
        reindex()

        def local(l: int) -> int:
            return (crossings_at(l - 1) if l > 0 else 0) + (crossings_at(l) if l + 1 < n_layers else 0)

        improved, passes = True, 0
        while improved and passes < 20:
            improved = False
            passes += 1
            for l in range(n_layers):
                r = rows[l]
                for i in range(len(r) - 1):
                    before = local(l)
                    ri, rj = r[i], r[i + 1]
                    if comp_idx[ri] != comp_idx[rj]:
                        continue
                    r[i], r[i + 1] = rj, ri
                    pos[rj], pos[ri] = i, i + 1
                    if local(l) < before:
                        improved = True
                    else:
                        r[i], r[i + 1] = ri, rj
                        pos[ri], pos[rj] = i, i + 1

    # 5. coordinates: layers along one axis, each layer centred on the widest, then relaxed toward the neighbours without overlap
    thick = [max((along(slots[node_id]["size"]) for node_id in r), default=0.0) for r in rows]
    at: list[float] = [0.0] * n_layers
    acc = 0.0
    for i, t in enumerate(thick):
        at[i] = acc
        acc += t + level_gap

    cross: dict[str, float] = {}

    def w_of(node_id: str) -> float:
        return across(slots[node_id]["size"])

    packed, hi = 0.0, 0.0
    for c in range(n_comp):
        mine = [[node_id for node_id in r if comp_idx[node_id] == c] for r in rows]
        members = [node_id for r in mine for node_id in r]
        if use_bk:
            bk = _brandes_koepf(mine, succ, pred, w_of, gap, lambda node_id: not slots[node_id]["real"])
            for node_id, x in bk.items():
                cross[node_id] = x
        else:

            def extent(r: list[str]) -> float:
                total = 0.0
                for i, node_id in enumerate(r):
                    total += w_of(node_id) + (gap if i else 0)
                return total

            widest = max((extent(r) for r in mine), default=0.0)
            for r in mine:
                a = (widest - extent(r)) / 2
                for node_id in r:
                    w = w_of(node_id)
                    cross[node_id] = a + w / 2
                    a += w + gap

            def settle(r: list[str], nb: dict[str, list[str]]) -> None:
                want = []
                for node_id in r:
                    ns = nb[node_id]
                    want.append((sum(cross[n] for n in ns) / len(ns)) if ns else cross[node_id])
                w = [w_of(node_id) for node_id in r]
                cs = list(want)
                for i in range(1, len(r)):
                    cs[i] = max(cs[i], cs[i - 1] + (w[i - 1] + w[i]) / 2 + gap)
                shift = sum(v - cs[i] for i, v in enumerate(want)) / max(1, len(r))
                for i in range(len(r)):
                    cs[i] = cs[i] + shift
                for i in range(1, len(r)):
                    cs[i] = max(cs[i], cs[i - 1] + (w[i - 1] + w[i]) / 2 + gap)
                for i, node_id in enumerate(r):
                    cross[node_id] = cs[i]

            for _t in range(3):
                for l in range(1, n_layers):
                    settle(mine[l], pred)
                for l in range(n_layers - 2, -1, -1):
                    settle(mine[l], succ)

        lo = min((cross[node_id] - w_of(node_id) / 2 for node_id in members), default=0.0)
        for node_id in members:
            cross[node_id] = cross[node_id] - lo + packed
        packed = max((cross[node_id] + w_of(node_id) / 2 for node_id in members), default=packed) + gap
        hi = packed - gap

    # outer lanes: past the boxes on the across side the return is assigned to
    lane_of: dict[int, float] = {}
    outers = [c for c in chains if c.get("outer")]
    outers.sort(key=lambda c: (abs(layer[c["e"]["from"]] - layer[c["e"]["to"]]), c["index"]))

    def low_side(c: dict) -> bool:
        side = outer_opt.get("side") if outer_opt else None
        return side == "low" or (side == "near" and (cross[c["e"]["from"]] + cross[c["e"]["to"]]) / 2 < hi / 2)

    lows = [c for c in outers if low_side(c)]
    highs = [c for c in outers if not low_side(c)]
    low_shift = (outer_opt["gap"] + (len(lows) - 1) * outer_opt["step"] + 2) if lows else 0.0
    for k, c in enumerate(lows):
        lane_of[c["index"]] = low_shift - outer_opt["gap"] - k * outer_opt["step"]
    for k, c in enumerate(highs):
        lane_of[c["index"]] = low_shift + hi + outer_opt["gap"] + k * outer_opt["step"]
    hi = low_shift + hi + ((outer_opt["gap"] + (len(highs) - 1) * outer_opt["step"] + 2) if highs else 0.0)

    def centre(node_id: str) -> dict:
        s = slots[node_id]
        a = at[s["layer"]] + thick[s["layer"]] / 2
        cr = cross[node_id] + low_shift
        return {"x": cr, "y": a} if dir_ == "down" else {"x": a, "y": cr}

    placed: dict[str, dict] = {}
    for n in nodes:
        p = centre(n["id"])
        placed[n["id"]] = {"x": p["x"] - n["size"]["w"] / 2, "y": p["y"] - n["size"]["h"] / 2, **n["size"]}

    edges_out: list[dict] = []
    for index, e in enumerate(edges):
        if e["from"] == e["to"]:
            edges_out.append({"from": e["from"], "to": e["to"], "index": index, "points": [centre(e["from"])], "reversed": False, "self": True})

    for c in chains:
        if c.get("outer"):
            a, b = centre(c["e"]["from"]), centre(c["e"]["to"])
            lane = lane_of[c["index"]]

            def at2(p: dict, d: float) -> dict:
                return {"x": lane, "y": p["y"] + d} if dir_ == "down" else {"x": p["x"] + d, "y": lane}

            edges_out.append(
                {"from": c["e"]["from"], "to": c["e"]["to"], "index": c["index"], "points": [a, at2(a, -1), at2(b, 1), b], "reversed": True, "self": False, "outer": True}
            )
            continue
        pts = [centre(i) for i in (list(reversed(c["ids"])) if c["rev"] else c["ids"])]
        edges_out.append({"from": c["e"]["from"], "to": c["e"]["to"], "index": c["index"], "points": pts, "reversed": c["rev"], "self": False})

    total = at[n_layers - 1] + thick[n_layers - 1]
    result: dict = {
        "nodes": placed,
        "edges": edges_out,
        "layers": dict(layer),
        "w": hi if dir_ == "down" else total,
        "h": total if dir_ == "down" else hi,
    }
    if folded:
        result["folded"] = folded
    return result
