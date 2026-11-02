"""1:1 port of lib/cause-hop.ts: where a return arrow of a cause tree crosses another line,
and which crossings get a hop (an arc over the other line) (ADR 0028). Pure geometry of the
laid-out figure: the layout calls it once and keeps the result in `LaidOutCause.crossings`;
the renderer only draws it.

Golden master: lib/cause-hop.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

HOP_R = 6
ARROW_L = 12
_BAR_HALF = 10

_STEP = {"up": {"x": 0, "y": -1}, "down": {"x": 0, "y": 1}, "right": {"x": 1, "y": 0}, "left": {"x": -1, "y": 0}}


def _width_of(e: dict) -> float:
    if e.get("kind") == "blocks":
        return 2
    return 3 if e.get("back") else 2


def _dist(a: dict, b: dict) -> float:
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def _inside(a: float, b: float, t: float) -> bool:
    return min(a, b) + 0.5 < t < max(a, b) - 0.5


def cause_crossings(edges: list[dict], flow: str, band: dict, boxes: list[dict], ands: list[dict], every_run: bool = False) -> list[dict]:
    """lib/cause-hop.ts:21-89 causeCrossings(): the crossings of every return's run across the
    layers (with `every_run`, of every arrow's run across the layers) with another line, in
    the order of the returns, each marked `skipped` when it gets no hop. `band`/`boxes` are
    the figure's/the nodes' boxes; `ands` the AND arcs [{p0, c, p1}]."""
    f = _STEP[flow]
    against = {"x": (0 - f["x"]) or 0, "y": (0 - f["y"]) or 0}

    def along_flow(a: dict, b: dict) -> bool:
        return a["y"] == b["y"] if f["x"] != 0 else a["x"] == b["x"]

    r = HOP_R
    x_margin = r + 2

    out: list[dict] = []
    for i, over in enumerate(edges):
        if (not over.get("reversed") and not every_run) or over.get("kind") == "blocks":
            continue
        found: list[dict] = []
        pts = over["points"]
        for si in range(len(pts) - 1):
            p, q = pts[si], pts[si + 1]
            if along_flow(p, q) or (p["x"] != q["x"] and p["y"] != q["y"]):
                continue
            for j, e in enumerate(edges):
                if j == i:
                    continue
                epts = e["points"]
                for k in range(len(epts) - 1):
                    u, v = epts[k], epts[k + 1]
                    sh = p["y"] == q["y"]
                    if (u["x"] != v["x"]) if sh else (u["y"] != v["y"]):
                        continue
                    x, y = (u["x"], p["y"]) if sh else (p["x"], u["y"])
                    ok = (_inside(p["x"], q["x"], x) and _inside(u["y"], v["y"], y)) if sh else (_inside(p["y"], q["y"], y) and _inside(u["x"], v["x"], x))
                    if not ok:
                        continue
                    found.append({"over": i, "under": j, "x": x, "y": y, "side": against, "si": si})

        for c in found:
            under = edges[c["under"]]
            x = x_margin
            under_pts = under["points"]
            skip: str | None = None
            here = {"x": c["x"], "y": c["y"]}
            s_run = [over["points"][c["si"]], over["points"][c["si"] + 1]]
            t_run: tuple[dict, dict, int] | None = None
            for k in range(len(under_pts) - 1):
                a, b = under_pts[k], under_pts[k + 1]
                if a["x"] == b["x"]:
                    if a["x"] == c["x"] and min(a["y"], b["y"]) < c["y"] < max(a["y"], b["y"]):
                        t_run = (a, b, k)
                        break
                elif a["y"] == b["y"] and a["y"] == c["y"] and min(a["x"], b["x"]) < c["x"] < max(a["x"], b["x"]):
                    t_run = (a, b, k)
                    break
            if over.get("line") != "solid":
                skip = "dashed"
            elif any(_dist(e, here) < x for e in s_run):
                skip = "corner"
            elif t_run is not None:
                last = t_run[2] + 2 == len(under_pts)
                tip = under_pts[-1]
                if under.get("kind") == "blocks" and last and _dist(tip, here) < x + _BAR_HALF:
                    skip = "bar"
                elif last and _dist(tip, here) < x + ARROW_L:
                    skip = "arrowhead"
                elif any(_dist(e, here) < x for e in (t_run[0], t_run[1])):
                    skip = "corner"
            if skip is None and any(o is not c and o["si"] == c["si"] and _dist(o, here) < 2 * x for o in found):
                skip = "neighbour"
            if skip is None and any(
                min(a["p0"]["x"], a["c"]["x"], a["p1"]["x"]) - x < c["x"] < max(a["p0"]["x"], a["c"]["x"], a["p1"]["x"]) + x
                and min(a["p0"]["y"], a["c"]["y"], a["p1"]["y"]) - x < c["y"] < max(a["p0"]["y"], a["c"]["y"], a["p1"]["y"]) + x
                for a in ands
            ):
                skip = "and-arc"
            if skip is None:
                apex = {"x": c["x"] + c["side"]["x"] * (r + 2), "y": c["y"] + c["side"]["y"] * (r + 2)}

                def in_rect(rect: dict, pt: dict) -> bool:
                    return rect["x"] < pt["x"] < rect["x"] + rect["w"] and rect["y"] < pt["y"] < rect["y"] + rect["h"]

                if not in_rect(band, apex) or any(in_rect(rect, apex) for rect in boxes):
                    skip = "band"
                else:
                    # a parallel line close beside the bulge: another run of the same direction as the one the hop is on, on the side it bulges to
                    r0, r1 = s_run[0], s_run[1]
                    horizontal = r0["y"] == r1["y"]
                    room = r + _width_of(over) / 2 + 1 + 2
                    near = False
                    for j, e in enumerate(edges):
                        if j == i:
                            continue
                        epts = e["points"]
                        for k in range(len(epts) - 1):
                            u, v = epts[k], epts[k + 1]
                            if (u["y"] != v["y"]) if horizontal else (u["x"] != v["x"]):
                                continue
                            off = (u["y"] - c["y"]) * c["side"]["y"] if horizontal else (u["x"] - c["x"]) * c["side"]["x"]
                            span = (min(u["x"], v["x"]), max(u["x"], v["x"]), c["x"]) if horizontal else (min(u["y"], v["y"]), max(u["y"], v["y"]), c["y"])
                            if off > 0 and off < room and span[2] > span[0] - (r + 2) and span[2] < span[1] + (r + 2):
                                near = True
                                break
                        if near:
                            break
                    if near:
                        skip = "parallel"
            entry = {"over": c["over"], "under": c["under"], "x": c["x"], "y": c["y"], "side": c["side"]}
            if skip:
                entry["skipped"] = skip
            out.append(entry)
    return out
