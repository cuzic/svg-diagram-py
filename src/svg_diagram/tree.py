"""1:1 port of lib/tree.ts's layoutTreeBand() (exported, golden-tested live) and
lib/emit-figures.ts's renderTree(). mindmap() is the same TreeBand with extra flags
(balanced/layout/sides/edges) stamped on — see lib/dsl/diagrams.ts:473-483 — so one
function covers both.

Scope note on lib/fit-width.ts's fitLayout(): tree()/mindmap() never need its generic
multi-stage search (keepWords retry, folding) — this port doesn't support keepWords, and
`foldable` is never set for tree/mindmap bands in Node either. What's left is a width x
direction grid search, always `mode: 'first'`-equivalent in practice (every attempt's score
is the fixed {crossings:0, bends:0}, so ties — which is every pair — never update "best",
meaning 'first' and 'best' pick the same, earliest-in-order, fitting attempt). That search
IS ported faithfully below (see `_search`), not simplified away.

Golden master: lib/tree.ts + lib/emit-figures.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .emit_common import emoji_span, js_round, snap4
from .emit_boxes import render_box_rect
from .graph_layout import layout_balanced, layout_tree
from .map_layouts import layout_brace, layout_fishbone, layout_hanging, layout_timeline_map, mirror
from .tokens import PALETTE, color_of, tone_style
from .tree_text import measure_node, node_runs

# lib/tree.ts:13 — tree.ts's OWN GAP/LEVEL_GAP, distinct from graph-layout.ts's defaults
# (24/40): layoutTreeBand always passes these explicitly, so graph-layout.ts's own fallback
# values are never actually used by tree()/mindmap().
GAP, LEVEL_GAP = 24, 44
NARROWING = [200, 160, 130, 110]
WIDEST = NARROWING[0]


def tree_items(root: dict) -> list[dict]:
    """lib/tree.ts:17-21 treeItems(): every item in drawing order (parent before children)."""
    out: list[dict] = []

    def walk(n: dict) -> None:
        out.append(n)
        for c in n.get("children") or []:
            walk(c)

    walk(root)
    return out


def layout_tree_band(
    root: dict,
    x: float,
    y: float,
    w: float,
    width_of,
    roles: dict,
    *,
    wrap_mode: str = "phrase",
    dir_opt: str | None = None,
    max_node_w: float | None = None,
    balanced: bool = False,
    layout_mode: str | None = None,
    sides: dict[str, str] | None = None,
    edges_opt: str | bool | None = None,
    space: float = 1,
) -> dict:
    """lib/tree.ts:81-165 layoutTreeBand()."""
    items = tree_items(root)
    seen: set[str] = set()
    for n in items:
        if not isinstance(n.get("label"), str) or not n["label"].strip():
            raise ValueError("tree(): every node needs a label")
        if n.get("id") is not None:
            if n["id"] in seen:
                raise ValueError(f'tree(): duplicate node id "{n["id"]}"')
            seen.add(n["id"])
    key = {id(n): f"n{i}" for i, n in enumerate(items)}

    def attempt_with(dir_now: str, max_w: float, floor: bool) -> dict:
        lines: dict[int, dict] = {}

        def build(n: dict) -> dict:
            m = measure_node(n["label"], n.get("sub"), max_w, width_of, roles, wrap_mode, floor)
            lines[id(n)] = m
            node = {"id": key[id(n)], "size": {"w": m["w"], "h": m["h"]}}
            children = n.get("children")
            if children:
                node["children"] = [build(c) for c in children]
            return node

        laid_root = build(root)
        sides_resolved: dict[str, str] = {}
        for node_id, side in (sides or {}).items():
            item = next((n for n in items if n.get("id") == node_id), None)
            if item is None:
                raise ValueError(f'mindmap(): sides names unknown node id "{node_id}"')
            if item not in (root.get("children") or []):
                raise ValueError(f'mindmap(): sides can pin only a child of the root ("{node_id}" is deeper)')
            sides_resolved[key[id(item)]] = side

        kind = (layout_mode or "radial") if balanced else dir_now
        if sides and kind != "radial":
            raise ValueError(f"mindmap(): sides applies to the radial layout (this is layout: '{kind}')")
        styled = edges_opt is not None and edges_opt != "elbow" and edges_opt is not False
        if styled and kind not in ("radial", "right", "left", "down", "up"):
            raise ValueError(f"mindmap(): edges: '{edges_opt}' applies to the radial, right, left, down and up layouts (this is layout: '{kind}')")

        def grown(d: str) -> dict:
            return layout_tree(laid_root, dir=d, gap=round(GAP * space), level_gap=round(LEVEL_GAP * space))

        if kind == "radial":
            raw = layout_balanced(laid_root, gap=round(GAP * space), level_gap=round(LEVEL_GAP * space), sides=sides_resolved)
        elif kind == "right":
            raw = grown("right")
        elif kind == "left":
            raw = mirror(grown("right"), "x")
        elif kind == "down":
            raw = grown("down")
        elif kind == "up":
            raw = mirror(grown("down"), "y")
        elif kind == "org":
            raw = layout_hanging(laid_root, row_first=True)
        elif kind == "list":
            raw = layout_hanging(laid_root)
        elif kind == "brace":
            raw = layout_brace(laid_root)
        elif kind == "fishbone":
            raw = layout_fishbone(laid_root)
        else:
            raw = layout_timeline_map(laid_root)

        along = "y" if kind in ("down", "up") else "x"
        if edges_opt is False:
            tree = {**raw, "edges": [e for e in raw["edges"] if e.get("bold")]}
        elif not styled:
            tree = raw
        else:
            new_edges = []
            for e in raw["edges"]:
                ne = {**e, "points": [e["points"][0], e["points"][-1]]}
                if edges_opt == "curve":
                    ne["curve"] = along
                new_edges.append(ne)
            tree = {**raw, "edges": new_edges}
        return {"size": {"w": tree["w"], "h": tree["h"]}, "tree": tree, "lines": lines}

    explicit_dir = not balanced and dir_opt is not None and dir_opt != "auto"
    start = "right" if dir_opt == "right" else "down"
    alt = None if balanced else ("right" if start == "down" else "down")
    free = not explicit_dir
    dirs = [start, alt] if (free and alt is not None) else [start]
    if max_node_w is not None:
        widths = [max_node_w]
    elif free:
        widths = NARROWING
    else:
        widths = [WIDEST]

    chosen = None
    for mw in widths:
        for d in dirs:
            result = attempt_with(d, mw, False)
            if result["size"]["w"] <= w + 0.5:
                chosen = result
                break
        if chosen:
            break
    if chosen is None:
        who = "mindmap()" if balanced else "tree()"
        raise ValueError(f"{who}: the figure does not fit the given width (tried {widths} x {dirs})")

    tree, lines = chosen["tree"], chosen["lines"]
    dx, dy = x + (w - tree["w"]) / 2, y
    out = {"x": x, "y": y, "w": w, "h": tree["h"], "nodes": [], "edges": [], "texts": [], "anchors": [], "labelBoxes": []}
    for n in items:
        p = tree["nodes"][key[id(n)]]
        l = lines[id(n)]
        r = {"x": p["x"] + dx, "y": p["y"] + dy, "w": p["w"], "h": p["h"]}
        node = {**r, "tone": n.get("tone") or "plain"}
        if n.get("id"):
            node["id"] = n["id"]
        out["nodes"].append(node)
        if n.get("id"):
            out["anchors"].append({"id": n["id"], **r})
        out["texts"].extend(node_runs(r, l, roles))
        out["labelBoxes"].append({"label": n["label"], **r})
    for e in tree["edges"]:
        entry = {"points": [{"x": p["x"] + dx, "y": p["y"] + dy} for p in e["points"]]}
        if e.get("curve"):
            entry["curve"] = e["curve"]
        if e.get("bold"):
            entry["bold"] = True
        out["edges"].append(entry)
    if tree.get("braces"):
        out["braces"] = [{**b, "x": b["x"] + dx, "tipX": b["tipX"] + dx, "y1": b["y1"] + dy, "y2": b["y2"] + dy, "ymid": b["ymid"] + dy} for b in tree["braces"]]
    return out


def render_tree(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:237-260 renderTree() (band-node children — tree({band: ...}) — are
    not supported by this port's model, so that branch never triggers here)."""
    dim = bool(b.get("dim"))
    out = []
    for e in b["edges"]:
        a, z = e["points"][0], e["points"][-1]
        if e.get("curve"):
            if e["curve"] == "x":
                d = f'M{snap4(a["x"])},{snap4(a["y"])} C{snap4((a["x"] + z["x"]) / 2)},{snap4(a["y"])} {snap4((a["x"] + z["x"]) / 2)},{snap4(z["y"])} {snap4(z["x"])},{snap4(z["y"])}'
            else:
                d = f'M{snap4(a["x"])},{snap4(a["y"])} C{snap4(a["x"])},{snap4((a["y"] + z["y"]) / 2)} {snap4(z["x"])},{snap4((a["y"] + z["y"]) / 2)} {snap4(z["x"])},{snap4(z["y"])}'
        else:
            d = "M" + " L".join(f'{snap4(p["x"])},{snap4(p["y"])}' for p in e["points"])
        width = 4 if e.get("bold") else 2
        out.append(f'<path d="{d}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="{width}"/>')
    for br in b.get("braces") or []:
        s = 1 if br["side"] == "right" else -1
        r = 8
        bx, xt, y1, y2, ym = snap4(br["x"]), snap4(br["tipX"]), snap4(br["y1"]), snap4(br["y2"]), snap4(br["ymid"])
        out.append(f'<path d="M{bx + s * r},{y1} Q{bx},{y1} {bx},{y1 + r} V{ym - r} Q{bx},{ym} {xt},{ym} Q{bx},{ym} {bx},{ym + r} V{y2 - r} Q{bx},{y2} {bx + s * r},{y2}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="2"/>')
    for n in b["nodes"]:
        if not n.get("band"):
            out.append(render_box_rect(x=n["x"], y=n["y"], w=n["w"], h=n["h"], tone=n.get("tone"), dim=dim, default_tone="plain"))
    nodes = b["nodes"]

    def ink(t: dict) -> str:
        if dim:
            return PALETTE["muted"]
        node = next((r for r in nodes if t["x"] >= r["x"] and t["x"] <= r["x"] + r["w"] and t["y"] > r["y"] and t["y"] <= r["y"] + r["h"]), None)
        if t.get("muted"):
            return PALETTE["text"] if (node and tone_style(node.get("tone")).fill == "soft") else PALETTE["muted"]
        return color_of(tone_style(node.get("tone") if node else None).text, day)

    for t in b["texts"]:
        bold_attr = ' font-weight="700"' if t.get("bold") else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}" text-anchor="middle" font-size="{t["size"]}"{bold_attr} fill="{ink(t)}">{emoji_span(t["text"])}</text>')
    return "\n  ".join(out)
