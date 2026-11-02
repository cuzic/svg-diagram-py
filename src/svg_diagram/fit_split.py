"""1:1 port of lib/fit-split.ts: what to say when a layered figure fits neither the width nor
the height (ADR 0019 D3) — where to draw it as two figures. Text only: nothing is split.

Golden master: lib/fit-split.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

_MAX_NAMES = 6


def _names(ids: list[str]) -> str:
    out = ", ".join(ids[:_MAX_NAMES])
    return out + ", …" if len(ids) > _MAX_NAMES else out


def split_by_height(lay: dict, budget: float) -> str | None:
    """lib/fit-split.ts:14-27 splitByHeight(): a figure too tall for its height budget (its
    layers lie along the height): the boundary between two layers where both halves fit the
    budget, with the fewest arrows across it, then the most even number of nodes. `lay` is in
    layout coordinates, the layers along x. A return (a reversed edge) is not counted. None
    fits: say that three or more figures are needed."""

    def layer_of(node_id: str) -> int:
        return lay["layers"][node_id]

    real = [{"id": node_id, "layer": layer_of(node_id), "from": p["x"], "to": p["x"] + p["w"]} for node_id, p in lay["nodes"].items()]
    top = max(n["layer"] for n in real)
    if top < 1:
        return None

    def span(ns: list[dict]) -> float:
        return (max(n["to"] for n in ns) - min(n["from"] for n in ns)) if ns else 0

    best: dict | None = None
    for k in range(top):
        up = [n for n in real if n["layer"] <= k]
        down = [n for n in real if n["layer"] > k]
        if span(up) > budget or span(down) > budget:
            continue
        across = [e for e in lay["edges"] if not e.get("self") and not e.get("reversed") and min(layer_of(e["from"]), layer_of(e["to"])) <= k and max(layer_of(e["from"]), layer_of(e["to"])) > k]
        cand = {"k": k, "across": [f"{e['from']}→{e['to']}" for e in across], "diff": abs(len(up) - len(down))}
        if best is None or len(cand["across"]) < len(best["across"]) or (len(cand["across"]) == len(best["across"]) and cand["diff"] < best["diff"]):
            best = cand
    if best is None:
        return "no cut between two layers leaves both halves within the height: three or more figures are needed"
    n_across = len(best["across"])
    return f"after layer {best['k'] + 1} ({n_across} arrow{'' if n_across == 1 else 's'} cross{'es' if n_across == 1 else ''}: {_names(best['across'])}). Draw the nodes up to that layer in one figure and the rest in another, repeating the nodes the arrows cross to in both"


def split_widest(lay: dict) -> str | None:
    """lib/fit-split.ts:30-44 splitWidest(): a figure too wide (one layer is wider than the
    figure): that layer and its nodes. A cut between layers does not help; the layer has to
    be shared out between two figures."""
    by_layer: dict[int, list[dict]] = {}
    for node_id, p in lay["nodes"].items():
        l = lay["layers"][node_id]
        by_layer.setdefault(l, []).append({"id": node_id, "from": p["y"], "to": p["y"] + p["h"]})
    widest: dict | None = None
    for layer, ns in by_layer.items():
        across = max(n["to"] for n in ns) - min(n["from"] for n in ns)
        if widest is None or across > widest["across"]:
            widest = {"layer": layer, "ids": [n["id"] for n in ns], "across": across}
    if widest is None or len(widest["ids"]) < 2:
        return None
    return f"layer {widest['layer'] + 1} is the widest ({len(widest['ids'])} nodes: {_names(widest['ids'])}). Share its nodes between two figures, each with the branch that leads from them"
