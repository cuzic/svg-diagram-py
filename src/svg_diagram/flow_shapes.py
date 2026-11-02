"""1:1 port of lib/flow-shapes.ts's layoutFlowShape() (exported, golden-tested live) for
chevron/valueChain/funnel/cycle/venn/concentric, and lib/emit-figures.ts's renderFlowShape().

NOT ported: emblem (layoutEmblem) — it additionally depends on lib/emblem-shapes.ts's
per-shape outline geometry (~13 shapes) and an iterative sizing search; deferred, see
BANDS.md.

Golden master: lib/flow-shapes.ts + lib/emit-figures.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import text_width
from .emit_common import emoji_span, js_round, snap4
from .tokens import PALETTE, color_of, resolve_box_style
from .tree_text import katakana_width
from .wrap import wrap_text

LINE = 1.35


def g4(v: float) -> float:
    return js_round(v / 4) * 4


def _node_of(item: dict) -> dict:
    return {"node": item["id"]} if item.get("id") else {}


class Texts:
    """lib/flow-shapes.ts:214-234 the Texts class."""

    def __init__(self, out: dict, width_of, roles: dict, mode: str) -> None:
        self.out = out
        self.width_of = width_of
        self.roles = roles
        self.mode = mode

    def wrap(self, text: str, max_w: float, weight: int = 700, size: float | None = None) -> dict:
        size = size if size is not None else self.roles["note"]
        lines = wrap_text(text, max_width=max(24, max_w), atom_width=lambda a: self.width_of(a, size, weight, "sans"), mode=self.mode)
        w = max([text_width(self.width_of, l, size, weight) for l in lines], default=0)
        return {"text": text, "lines": lines, "h": len(lines) * size * LINE, "w": w, "size": size, "weight": weight}

    def width(self, text: str, weight: int = 700, size: float | None = None) -> float:
        size = size if size is not None else self.roles["note"]
        return text_width(self.width_of, text, size, weight)

    def place(self, block: dict, x: float, top: float, tone: str = "text", anchor: str = "middle") -> None:
        size, weight = block["size"], block["weight"]
        for i, line in enumerate(block["lines"]):
            tw = text_width(self.width_of, line, size, weight)
            ty = top + i * size * LINE + size * ((LINE - 1.2) / 2 + 1)
            left = x - tw / 2 if anchor == "middle" else (x if anchor == "start" else x - tw)
            box = {"x": left, "y": ty - size, "w": tw, "h": size * 1.2}
            self.out["texts"].append({"text": line, "tx": x, "ty": ty, "size": size, "weight": weight, "anchor": anchor, "tone": tone, **box})
            self.out["labelBoxes"].append({"label": block["text"], **box})


def chevron_band(steps: list[dict], *, direction: str | None = None, first: str | None = None, gap: float | None = None, current: int | None = None, width: float | None = None, id: str | None = None) -> dict:
    """lib/flow-shapes.ts:74-84 chevronBand() (defaults only — loopBack/scope validation not ported)."""
    band = {"type": "chevron", "steps": list(steps), "direction": direction or "horizontal", "first": first or "pentagon", "gap": gap if gap is not None else 4}
    if current is not None:
        band["current"] = current
    if width is not None:
        band["width"] = width
    if id is not None:
        band["id"] = id
    return band


def funnel_band(stages: list[dict], *, scale: str | None = None, show_rate: bool = False, width: float | None = None, id: str | None = None) -> dict:
    """lib/flow-shapes.ts:85-93 funnelBand()."""
    band = {"type": "funnel", "stages": list(stages), "scale": scale or "even", "showRate": show_rate}
    if width is not None:
        band["width"] = width
    if id is not None:
        band["id"] = id
    return band


def cycle_band(steps: list[dict], *, direction: str | None = None, centre: str | None = None, width: float | None = None, id: str | None = None) -> dict:
    """lib/flow-shapes.ts:94-100 cycleBand()."""
    if not (3 <= len(steps) <= 8):
        raise ValueError(f"cycle(): needs 3..8 steps (got {len(steps)})")
    band = {"type": "cycle", "steps": list(steps), "direction": direction or "cw"}
    if centre is not None:
        band["centre"] = centre
    if width is not None:
        band["width"] = width
    if id is not None:
        band["id"] = id
    return band


def venn_band(sets: list[dict], *, overlaps: list[dict] | None = None, centre: str | None = None, universe: str | bool | None = None, width: float | None = None, id: str | None = None) -> dict:
    """lib/flow-shapes.ts:101-119 vennBand()."""
    if not (2 <= len(sets) <= 3):
        raise ValueError(f"venn(): needs 2 or 3 sets (got {len(sets)})")
    band = {"type": "venn", "sets": list(sets), "overlaps": list(overlaps or [])}
    if centre is not None:
        band["centre"] = centre
    if universe is not None:
        band["universe"] = universe
    if width is not None:
        band["width"] = width
    if id is not None:
        band["id"] = id
    return band


def concentric_band(rings: list[dict], *, order: str | None = None, labels: str | None = None, centre: str | None = None, width: float | None = None, id: str | None = None) -> dict:
    """lib/flow-shapes.ts:120-125 concentricBand()."""
    band = {"type": "concentric", "rings": list(rings), "order": order or "outer-first", "labels": labels or "inside"}
    if centre is not None:
        band["centre"] = centre
    if width is not None:
        band["width"] = width
    if id is not None:
        band["id"] = id
    return band


def value_chain_band(*, support: list[dict] | None = None, primary: list[dict], margin: str | bool | None = None, titles: tuple[str, str] | bool | None = None, width: float | None = None, id: str | None = None) -> dict:
    """lib/flow-shapes.ts:143-154 valueChainBand(). `margin`/`titles` False means "leave it out";
    None (omitted) means the Japanese defaults — NOT falsy/absent, matching Node's `?? default`."""
    band = {
        "type": "valueChain",
        "support": list(support or []),
        "primary": list(primary),
        "margin": "マージン" if margin is None else margin,
        "titles": ("支援活動", "主活動") if titles is None else titles,
    }
    if width is not None:
        band["width"] = width
    if id is not None:
        band["id"] = id
    return band


def layout_flow_shape(b: dict, x: float, y: float, cw: float, width_of, roles: dict, mode: str) -> dict:
    """lib/flow-shapes.ts:195-210 layoutFlowShape()."""
    w = min(cw, b.get("width") or cw)
    ox = x + (cw - w) / 2
    out = {"type": b["type"], "x": ox, "y": y, "w": w, "h": 0, "primitives": [], "texts": [], "anchors": [], "labelBoxes": []}
    if b.get("id"):
        out["id"] = b["id"]
    t = Texts(out, width_of, roles, mode)

    def anchor(item_id: str | None, r: dict) -> None:
        if item_id:
            out["anchors"].append({"id": item_id, **r})

    kind = b["type"]
    if kind == "chevron":
        _layout_chevron(b, out, t, anchor)
    elif kind == "funnel":
        _layout_funnel(b, out, t, anchor, roles)
    elif kind == "cycle":
        _layout_cycle(b, out, t, anchor, roles)
    elif kind == "venn":
        _layout_venn(b, out, t, anchor)
    elif kind == "concentric":
        _layout_concentric(b, out, t, anchor, roles)
    elif kind == "valueChain":
        _layout_value_chain(b, out, t, anchor)
    else:
        raise NotImplementedError(f"layout_flow_shape(): {kind!r} is not supported by this port (emblem needs lib/emblem-shapes.ts, not ported)")
    return out


def _layout_chevron(b: dict, out: dict, t: Texts, anchor) -> None:
    """lib/flow-shapes.ts:236-257 layoutChevron()."""
    vertical = b.get("direction") == "vertical"
    n = len(b["steps"])
    current = b.get("current", b.get("highlight"))
    cell_w = (out["w"] if b.get("width") else min(360, out["w"])) if vertical else (out["w"] - b["gap"] * (n - 1)) / n
    tip = 16 if vertical else min(22, cell_w / 4)
    text_w = cell_w - 24 if vertical else cell_w - 2 * tip - 8
    blocks = [{"label": t.wrap(s["label"], text_w), "sub": t.wrap(s["sub"], text_w, 400) if s.get("sub") else None} for s in b["steps"]]

    def text_h(k: dict) -> float:
        return k["label"]["h"] + (k["sub"]["h"] if k["sub"] else 0)

    cell_h = max(60, max(text_h(k) for k in blocks) + 20 + (tip if vertical else 0))
    out["h"] = n * cell_h + (n - 1) * b["gap"] if vertical else cell_h
    for i, s in enumerate(b["steps"]):
        xx = out["x"] + (out["w"] - cell_w) / 2 if vertical else out["x"] + i * (cell_w + b["gap"])
        yy = out["y"] + i * (cell_h + b["gap"]) if vertical else out["y"]
        notch = [[xx + tip, yy + cell_h / 2]] if (i or b.get("first") == "chevron") else []
        if vertical:
            points = [[xx, yy], [xx + cell_w, yy], [xx + cell_w, yy + cell_h - tip], [xx + cell_w / 2, yy + cell_h], [xx, yy + cell_h - tip]]
        else:
            points = [[xx, yy], [xx + cell_w - tip, yy], [xx + cell_w, yy + cell_h / 2], [xx + cell_w - tip, yy + cell_h], [xx, yy + cell_h], *notch]
        tone = "accent" if current == i else s.get("tone", "plain")
        prim = {"k": "polygon", "points": points, "tone": tone, **_node_of(s)}
        if current == i:
            prim["strong"] = True
        out["primitives"].append(prim)
        anchor(s.get("id"), {"x": xx, "y": yy, "w": cell_w, "h": cell_h})
        k = blocks[i]
        top = yy + (cell_h - (tip if vertical else 0) - text_h(k)) / 2
        t.place(k["label"], xx + cell_w / 2, top)
        if k["sub"]:
            t.place(k["sub"], xx + cell_w / 2, top + k["label"]["h"], "muted")


def _layout_value_chain(b: dict, out: dict, t: Texts, anchor) -> None:
    """lib/flow-shapes.ts:259-309 layoutValueChain()."""
    gap, tip_m = 4, 20
    margin = b.get("margin")
    margin_w = min(140, max(76, t.width(margin) + tip_m + 16)) if margin else 0
    main_w = out["w"] - (margin_w + 8 if margin else 0)
    y = out["y"]

    def title(text: str | None) -> None:
        nonlocal y
        if not text:
            return
        k = t.wrap(text, main_w)
        t.place(k, out["x"], y, "muted", "start")
        y += k["h"] + 6

    titles = b.get("titles")
    top = y
    if b["support"]:
        title(titles[0] if titles else None)
        for s in b["support"]:
            label = t.wrap(s["label"], main_w - 24)
            sub = t.wrap(s["sub"], main_w - 24, 400) if s.get("sub") else None
            h = max(36, label["h"] + (sub["h"] if sub else 0) + 16)
            text_top = y + (h - label["h"] - (sub["h"] if sub else 0)) / 2
            out["primitives"].append({"k": "polygon", "points": [[out["x"], y], [out["x"] + main_w, y], [out["x"] + main_w, y + h], [out["x"], y + h]], "tone": s.get("tone", "muted"), **_node_of(s)})
            anchor(s.get("id"), {"x": out["x"], "y": y, "w": main_w, "h": h})
            t.place(label, out["x"] + main_w / 2, text_top)
            if sub:
                t.place(sub, out["x"] + main_w / 2, text_top + label["h"], "muted")
            y += h + gap
        y += 8 - gap

    title(titles[1] if titles else None)
    n = len(b["primary"])
    cell_w = (main_w - gap * (n - 1)) / n
    tip = min(18, cell_w / 4)
    text_w = cell_w - 2 * tip - 4
    blocks = [{"label": t.wrap(s["label"], text_w), "sub": t.wrap(s["sub"], text_w, 400) if s.get("sub") else None} for s in b["primary"]]

    def text_h(k: dict) -> float:
        return k["label"]["h"] + (k["sub"]["h"] if k["sub"] else 0)

    cell_h = max(72, max(text_h(k) for k in blocks) + 24)
    for i, s in enumerate(b["primary"]):
        xx, yy = out["x"] + i * (cell_w + gap), y
        notch = [[xx + tip, yy + cell_h / 2]] if i else []
        out["primitives"].append({"k": "polygon", "points": [[xx, yy], [xx + cell_w - tip, yy], [xx + cell_w, yy + cell_h / 2], [xx + cell_w - tip, yy + cell_h], [xx, yy + cell_h], *notch], "tone": s.get("tone", "plain"), **_node_of(s)})
        anchor(s.get("id"), {"x": xx, "y": yy, "w": cell_w, "h": cell_h})
        k = blocks[i]
        text_top = yy + (cell_h - text_h(k)) / 2
        t.place(k["label"], xx + cell_w / 2, text_top)
        if k["sub"]:
            t.place(k["sub"], xx + cell_w / 2, text_top + k["label"]["h"], "muted")
    bottom = y + cell_h
    if margin:
        mx, mid = out["x"] + out["w"] - margin_w, (top + bottom) / 2
        out["primitives"].append({"k": "polygon", "points": [[mx, top], [mx + margin_w - tip_m, top], [mx + margin_w, mid], [mx + margin_w - tip_m, bottom], [mx, bottom]], "tone": "accent", "strong": True})
        label = t.wrap(margin, margin_w - tip_m - 4)
        t.place(label, mx + (margin_w - tip_m) / 2, mid - label["h"] / 2)
    out["h"] = bottom - out["y"]


def _layout_funnel(b: dict, out: dict, t: Texts, anchor, roles: dict) -> None:
    """lib/flow-shapes.ts:311-340 layoutFunnel()."""
    n = len(b["stages"])
    w, cx = out["w"], out["x"] + out["w"] / 2
    min_w = min(150, w * 0.3)
    max_v = max([s.get("value", 0) for s in b["stages"]] + [1])

    def frac(i: int) -> float:
        if b["scale"] == "value":
            return b["stages"][i].get("value", 0) / max_v
        return 1 if n == 1 else 1 - i * 0.65 / (n - 1)

    tops = [max(min_w, w * frac(i)) for i in range(n)]
    bottoms = [tops[i + 1] if i < n - 1 else max(min_w * 0.8, tops[i] * 0.8) for i in range(n)]
    lh = roles["note"] * LINE

    def funnel_label(s: dict) -> str:
        return s["label"] if s.get("value") is None else f"{s['label']}  {s['value']}"

    def funnel_rate(prev, v) -> str | None:
        if prev and v is not None:
            return f"{round(v / prev * 100)}%"
        return None

    plans = []
    for i, s in enumerate(b["stages"]):
        text = funnel_label(s)
        ti, bi = tops[i], bottoms[i]
        inner = min(ti, bi) - 24
        side_left = cx + max(ti, bi) / 2 + 14
        side_w = out["x"] + w - side_left
        beside = t.width(text) > inner and side_w >= 80
        label = t.wrap(text, side_w if beside else inner)
        rate_text = funnel_rate(b["stages"][i - 1].get("value"), s.get("value")) if (b.get("showRate") and i) else None
        rate = t.wrap(rate_text, w, 400) if rate_text else None
        rate_left = rate is not None and cx - max(ti, bi) / 2 - 14 - rate["w"] >= out["x"]
        plans.append({"label": label, "beside": beside, "sideLeft": side_left, "rate": rate, "rateLeft": rate_left})

    row_h = max([64] + [p["label"]["h"] + (p["rate"]["h"] if (p["rate"] and not p["rateLeft"]) else 0) + 20 for p in plans])
    out["h"] = n * row_h
    for i, s in enumerate(b["stages"]):
        yy = out["y"] + i * row_h
        a, z, p = tops[i], bottoms[i], plans[i]
        tone = s.get("tone") or ("muted" if i % 2 else "accent")
        out["primitives"].append({"k": "polygon", "points": [[cx - a / 2, yy], [cx + a / 2, yy], [cx + z / 2, yy + row_h - 4], [cx - z / 2, yy + row_h - 4]], "tone": tone, **_node_of(s)})
        anchor(s.get("id"), {"x": cx - max(a, z) / 2, "y": yy, "w": max(a, z), "h": row_h - 4})
        block_h = p["label"]["h"] + (p["rate"]["h"] if (p["rate"] and not p["rateLeft"]) else 0)
        top = yy + (row_h - 4 - block_h) / 2
        lx = p["sideLeft"] if p["beside"] else cx
        la = "start" if p["beside"] else "middle"
        t.place(p["label"], lx, top, "text", la)
        if p["rate"]:
            if p["rateLeft"]:
                t.place(p["rate"], cx - max(a, z) / 2 - 14, yy + (row_h - 4 - lh) / 2, "muted", "end")
            else:
                t.place(p["rate"], lx, top + p["label"]["h"], "muted", la)


def _layout_cycle(b: dict, out: dict, t: Texts, anchor, roles: dict) -> None:
    """lib/flow-shapes.ts:342-377 layoutCycle()."""
    w, n = out["w"], len(b["steps"])
    h0 = min(520, max(300, w * 0.62))
    sin_n = math.sin(math.pi / n)
    arrow_room = 20
    r = min(w, h0) * 0.34
    nr = max(28, min(54, r * 0.38, r * sin_n - 14))
    word = max([0.0] + [max(katakana_width(s["label"], t.width_of, roles["note"], 700), katakana_width(s["sub"], t.width_of, roles["note"], 400) if s.get("sub") else 0) for s in b["steps"]])
    if word > nr * 1.5:
        want = math.ceil(word / 1.5)
        r_max = min(w / 2 - 4 - want, (760 - 16) / 2 - want)
        r_need = max(r, 2 * want, (want + arrow_room) / sin_n)
        if r_max > r:
            r = min(r_need, r_max)
            nr = max(nr, min(want, r * 0.5, r * sin_n - arrow_room))
    h = max(h0, 2 * (r + nr) + 16)
    out["h"] = h
    cx, cy = out["x"] + w / 2, out["y"] + h / 2
    sign = 1 if b["direction"] == "cw" else -1

    def angle(i: int) -> float:
        return -math.pi / 2 + sign * 2 * math.pi * i / n

    def at(a: float, radius: float = r) -> list[float]:
        return [cx + radius * math.cos(a), cy + radius * math.sin(a)]

    skip = 2 * math.asin(min(1, (nr + 8) / (2 * r)))

    def r1(v: float) -> float:
        return round(v * 10) / 10

    for i in range(n):
        p = at(angle(i) + sign * skip)
        q = at(angle(i + 1) - sign * skip)
        d = f"M{r1(p[0])},{r1(p[1])} A{r1(r)},{r1(r)} 0 0 {1 if sign > 0 else 0} {r1(q[0])},{r1(q[1])}"
        out["primitives"].append({"k": "path", "d": d, "tone": "text", "arrow": True})
    for i, s in enumerate(b["steps"]):
        ax, ay = at(angle(i))
        nx, ny = g4(ax), g4(ay)
        tone = "danger" if s.get("tone") in ("danger", "removed") else ("muted" if s.get("tone") == "muted" else "accent")
        out["primitives"].append({"k": "circle", "cx": nx, "cy": ny, "r": nr, "tone": tone, **_node_of(s)})
        anchor(s.get("id"), {"x": nx - nr, "y": ny - nr, "w": 2 * nr, "h": 2 * nr})
        label = t.wrap(s["label"], nr * 1.5)
        sub = t.wrap(s["sub"], nr * 1.5, 400) if s.get("sub") else None
        top = ny - (label["h"] + (sub["h"] if sub else 0)) / 2
        t.place(label, nx, top)
        if sub:
            t.place(sub, nx, top + label["h"], "muted")
    if b.get("centre"):
        c = t.wrap(b["centre"], 1.5 * (r - nr), 700, roles["label"])
        t.place(c, cx, cy - c["h"] / 2)


def _layout_venn(b: dict, out: dict, t: Texts, anchor) -> None:
    """lib/flow-shapes.ts:379-411 layoutVenn()."""
    w = out["w"]
    three = len(b["sets"]) == 3
    uni = bool(b.get("universe"))
    r = min(w * 0.21, 170) if three else min(w * 0.23, 190)
    above = 1.28 * r if three else r
    below = 1.52 * r if three else r
    pad_top = 40 if uni else 8
    pad_bottom = 20 if uni else 8
    out["h"] = pad_top + above + below + pad_bottom
    cx, cy = out["x"] + w / 2, out["y"] + pad_top + above
    if three:
        raw_pos = [[cx - r * 0.55, cy - r * 0.28], [cx + r * 0.55, cy - r * 0.28], [cx, cy + r * 0.52]]
    else:
        raw_pos = [[cx - r * 0.58, cy], [cx + r * 0.58, cy]]
    pos = [[g4(p[0]), g4(p[1])] for p in raw_pos]
    mid = [sum(p[0] for p in pos) / len(pos), sum(p[1] for p in pos) / len(pos)]
    if uni:
        fx, fy = g4(out["x"] + 4), g4(out["y"] + 4)
        out["primitives"].append({"k": "rect", "x": fx, "y": fy, "w": g4(out["x"] + w - 4) - fx, "h": g4(out["y"] + out["h"] - 4) - fy, "tone": "muted"})
        if isinstance(b.get("universe"), str):
            t.place(t.wrap(b["universe"], w - 32, 400), out["x"] + 16, out["y"] + 10, "muted", "start")
    dash = ["", "7,5", "2,4"]
    tones = ["accent", "danger", "muted"]

    def centred(text: str, p: list[float], max_w: float) -> None:
        k = t.wrap(text, max_w)
        t.place(k, p[0], p[1] - k["h"] / 2)

    for i, s in enumerate(b["sets"]):
        px, py = pos[i]
        dx, dy = px - mid[0], py - mid[1]
        dist = math.hypot(dx, dy) or 1
        k = 0.5 if three else 0.42
        prim = {"k": "circle", "cx": px, "cy": py, "r": r, "tone": s.get("tone") or tones[i], "opacity": 0.22, **_node_of(s)}
        if dash[i]:
            prim["dash"] = dash[i]
        out["primitives"].append(prim)
        anchor(s.get("id"), {"x": px - r, "y": py - r, "w": 2 * r, "h": 2 * r})
        centred(s.get("label") or s["name"], [px + dx / dist * k * r, py + dy / dist * k * r], 0.8 * r)
    for o in b["overlaps"]:
        idx = [next(i for i, s in enumerate(b["sets"]) if s["name"] == name) for name in o["sets"]]
        if len(idx) == len(b["sets"]):
            centred(o["label"], mid, (0.55 if three else 0.7) * r)
            continue
        p, q = pos[idx[0]], pos[idx[1]]
        third = pos[next(j for j in (0, 1, 2) if j not in idx)]
        m = [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2]
        d_val = math.hypot(m[0] - third[0], m[1] - third[1])
        half = math.sqrt(r * r - (math.hypot(p[0] - q[0], p[1] - q[1]) / 2) ** 2)
        reach = (r + d_val + half) / 2
        centred(o["label"], [third[0] + (m[0] - third[0]) / d_val * reach, third[1] + (m[1] - third[1]) / d_val * reach], 0.5 * r)
    if b.get("centre"):
        centred(b["centre"], mid, (0.55 if three else 0.7) * r)


def _layout_concentric(b: dict, out: dict, t: Texts, anchor, roles: dict) -> None:
    """lib/flow-shapes.ts:413-455 layoutConcentric()."""
    w = out["w"]
    side = b["labels"] == "side"
    n = len(b["rings"])
    lh = roles["note"] * LINE
    ordered = b["rings"] if b["order"] == "outer-first" else list(reversed(b["rings"]))
    r = min(200, w * 0.3) if side else min(220, w * 0.42)

    def radius(i: int) -> float:
        return r * (n - i) / n

    key_w = w - 2 * r - 64

    def ring_label(ring: dict) -> str:
        return f"{ring['label']} — {ring['description']}" if ring.get("description") else ring["label"]

    keys = [t.wrap(ring_label(ring), key_w) for ring in ordered] if side else []
    left = max(out["x"] + 8, g4(out["x"] + (w - (2 * r + 48 + (max((k["w"] for k in keys), default=0)))) / 2)) if side else out["x"] + 16
    key_left = left + 2 * r + 48
    key_h = sum(k["h"] + 12 for k in keys)
    out["h"] = max(2 * r + 16, key_h + 16)
    cx = g4(left + r if side else out["x"] + w / 2)
    cy = g4(out["y"] + out["h"] / 2)
    tones = ["accent", "muted", "danger", "text"]
    for i, ring in enumerate(ordered):
        rr = radius(i)
        prim = {"k": "circle", "cx": cx, "cy": cy, "r": rr, "tone": ring.get("tone") or tones[i % 4], "opacity": 0.10 + (i % 2) * 0.05, **_node_of(ring)}
        if i % 2:
            prim["dash"] = "7,5"
        out["primitives"].append(prim)
        anchor(ring.get("id"), {"x": cx - rr, "y": cy - rr, "w": 2 * rr, "h": 2 * rr})
    if side:
        slot = (out["h"] - 16) / n
        for i, ring in enumerate(ordered):
            k = keys[i]
            top = out["y"] + 8 + i * slot + (slot - k["h"]) / 2
            ly = top + min(k["h"], lh) / 2
            rm = (radius(i) + (radius(i + 1) if i < n - 1 else 0)) / 2
            a = -math.pi / 6
            dot = [g4(cx + rm * math.cos(a)), g4(cy + rm * math.sin(a))]
            out["primitives"].append({"k": "path", "d": f"M{dot[0]:.1f},{dot[1]:.1f} L{key_left - 8:.1f},{ly:.1f}", "tone": "muted", "thin": True})
            out["primitives"].append({"k": "circle", "cx": dot[0], "cy": dot[1], "r": 3.5, "tone": "text", "opacity": 1})
            t.place(k, key_left, top, ring.get("tone") or "text", "start")
    inner_bottom = -math.inf
    if not side:
        for i, ring in enumerate(ordered):
            rr = radius(i)
            mid = (rr + (radius(i + 1) if i < n - 1 else 0)) / 2

            def chord(h: float) -> float:
                return 2 * math.sqrt(max(0, rr * rr - (mid + h / 2) ** 2)) - 12

            k = t.wrap(ring_label(ring), max(60, chord(lh)))
            tries = 0
            while tries < 3 and k["w"] > chord(k["h"]) and chord(k["h"]) >= 60:
                k = t.wrap(ring_label(ring), chord(k["h"]))
                tries += 1
            top = cy - mid - k["h"] / 2
            t.place(k, cx, top, ring.get("tone") or "text")
            inner_bottom = top + k["h"]
    if b.get("centre"):
        c = t.wrap(b["centre"], max(60, 1.4 * radius(n - 1)))
        t.place(c, cx, max(cy - c["h"] / 2, inner_bottom + 4))


def render_flow_shape(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:188-213 renderFlowShape()."""
    dim = bool(b.get("dim"))

    def ink(c: str) -> str:
        return PALETTE["muted"] if dim else c

    def paper(c: str) -> str:
        return PALETTE["bg"] if dim else c

    def n(v: float) -> str:
        from .emit_common import js_num

        return js_num(round(v * 10) / 10)

    def dn(p: dict) -> str:
        # ADR 0034: `dataNode` is set by the withNodeIds pass, which this port doesn't run —
        # so this is always "" here, matching an un-transformed Node output exactly.
        from .emit_common import escape_attr

        return f' data-node="{escape_attr(p["dataNode"])}"' if p.get("dataNode") else ""

    out = []
    for p in b["primitives"]:
        if p["k"] == "polygon":
            s = resolve_box_style(p.get("tone"), day)
            pts = " ".join(f"{n(q[0])},{n(q[1])}" for q in p["points"])
            dash = ' stroke-dasharray="6,4"' if s["dashed"] else ""
            sw = 3.5 if p.get("strong") else 2
            out.append(f'<polygon points="{pts}" fill="{paper(s["fill"])}" stroke="{ink(s["stroke"])}" stroke-width="{sw}"{dash}{dn(p)}/>')
        elif p["k"] == "circle" and p.get("fill"):
            st = resolve_box_style(p["fill"], day)
            dash = ' stroke-dasharray="6,4"' if st["dashed"] else ""
            out.append(f'<circle cx="{n(p["cx"])}" cy="{n(p["cy"])}" r="{n(p["r"])}" fill="{paper(st["fill"])}" stroke="{ink(st["stroke"])}" stroke-width="2"{dash}{dn(p)}/>')
        elif p["k"] == "circle":
            c = ink(color_of(p["tone"], day))
            dash = f' stroke-dasharray="{p["dash"]}"' if p.get("dash") else ""
            out.append(f'<circle cx="{n(p["cx"])}" cy="{n(p["cy"])}" r="{n(p["r"])}" fill="{c}" fill-opacity="{p.get("opacity", 0.16)}" stroke="{c}" stroke-width="2"{dash}{dn(p)}/>')
        elif p["k"] == "rect":
            out.append(f'<rect x="{n(p["x"])}" y="{n(p["y"])}" width="{n(p["w"])}" height="{n(p["h"])}" rx="8" fill="none" stroke="{ink(color_of(p["tone"], day))}" stroke-width="2"/>')
        elif p.get("fill"):
            st = resolve_box_style(p["fill"], day)
            dash = ' stroke-dasharray="6,4"' if st["dashed"] else ""
            out.append(f'<path d="{p["d"]}" fill="{paper(st["fill"])}" stroke="{ink(st["stroke"])}" stroke-width="2"{dash}{dn(p)}/>')
        else:
            arrow_attr = f' marker-end="url(#{"dsl-arrow-dim" if b.get("dim") else "dsl-arrow"})"' if p.get("arrow") else ""
            out.append(f'<path d="{p["d"]}" fill="none" stroke="{ink(color_of(p["tone"], day))}" stroke-width="{1.5 if p.get("thin") else 2}"{arrow_attr}/>')
    for tx in b["texts"]:
        anchor_attr = "" if tx["anchor"] == "start" else f' text-anchor="{tx["anchor"]}"'
        weight_attr = f' font-weight="{tx["weight"]}"'
        out.append(f'<text x="{n(tx["tx"])}" y="{n(tx["ty"])}"{anchor_attr} font-size="{tx["size"]}"{weight_attr} fill="{ink(color_of(tx["tone"], day))}">{emoji_span(tx["text"])}</text>')
    return "\n  ".join(out)
