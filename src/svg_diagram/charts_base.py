"""1:1 port of lib/charts-base.ts — the shared ground of the consulting-style charts
(waterfall, radar, heatmap, stacked bars / mekko, treemap, sankey, tornado): a small canvas
that collects what a chart draws and finds a free spot for a label.

Golden master: lib/charts-base.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from .atoms import split_atoms, text_width
from .emit_common import js_num, js_round, round1
from .wrap import wrap_atoms


def overlaps(a: dict, b: dict) -> bool:
    """lib/charts-base.ts:55 overlaps()."""
    return min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]) > 0.5 and min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]) > 0.5


def seg_hits_rect(sg: dict, r: dict) -> bool:
    """lib/bars.ts:137-146 segHitsRect() (Liang-Barsky) — lives here (not in bars.py) because
    Canvas.free() needs it too and charts-base.ts imports it from bars.ts in Node; bars.py
    imports it back from here to avoid a Python import cycle."""
    t0, t1 = 0.0, 1.0
    dx, dy = sg["x2"] - sg["x1"], sg["y2"] - sg["y1"]
    for p, q in ((-dx, sg["x1"] - r["x"]), (dx, r["x"] + r["w"] - sg["x1"]), (-dy, sg["y1"] - r["y"]), (dy, r["y"] + r["h"] - sg["y1"])):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            if t > t1:
                return False
            t0 = max(t0, t)
        else:
            if t < t0:
                return False
            t1 = min(t1, t)
    return t0 <= t1


def fail(who: str, msg: str):
    """lib/charts-base.ts:196 fail()."""
    raise ValueError(f"{who}(): {msg}")


def finite_num(who: str, what: str, v, min: float | None = None) -> float:
    """lib/charts-base.ts:197-201 finiteNum()."""
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or abs(v) >= 1e15:
        fail(who, f"{what} must be a finite number (got {v})")
    if min is not None and v < min:
        fail(who, f"{what} must be >= {min} (got {v})")
    return v


def check_text(who: str, what: str, v) -> str:
    """lib/charts-base.ts:202-205 checkText()."""
    if not isinstance(v, str) or not v.strip():
        fail(who, f"{what} must be a non-empty string")
    return v


def check_ids(who: str, ids: list, band_id: str | None) -> None:
    """lib/charts-base.ts:206-210 checkIds()."""
    given = [i for i in ids if i]
    if len(set(given)) != len(given):
        fail(who, "each id must be unique")
    if band_id is not None and band_id in given:
        fail(who, f'the band\'s id "{band_id}" is also an element\'s id — each id must be unique')


_SHADE_LADDER: dict[int, list[float]] = {1: [0.5], 2: [0.25, 0.7], 3: [0.15, 0.5, 0.85], 4: [0.12, 0.35, 0.6, 0.85], 5: [0.1, 0.3, 0.5, 0.7, 0.9], 6: [0.1, 0.25, 0.4, 0.55, 0.7, 0.9]}

# The tone/dash ladder the seaborn-style multi-group charts (distplot/multiplot/regplot) use
# to tell up to 4 groups apart — each of lib/charts-dist.ts / lib/charts-multi.ts /
# lib/charts-reg.ts redefines this pair of constants verbatim; hoisted here once.
CHART_TONES: list[str] = ["accent", "danger", "text", "muted"]
CHART_DASH: list[str] = ["", "6,4", "2,4", "10,4,2,4"]


def shade_ops(count: int) -> list[float]:
    """lib/charts-base.ts:211-215 shadeOps()."""
    return _SHADE_LADDER.get(count, _SHADE_LADDER[6])


def ink_on_shade(op: float) -> str:
    """lib/charts-base.ts:217 inkOnShade()."""
    return "bg" if op >= 0.6 else "text"


# lib/charts-cat.ts's own SHAPES/markerPath, hoisted here (rather than kept in catplot.py,
# where Node's source puts them) because lib/charts-multi.ts and lib/charts-reg.ts import
# them sideways from charts-cat.ts too — a chart-kind module (multiplot/regplot) having a
# dependency on an unrelated chart-kind module (catplot) purely for a generic marker-drawing
# primitive is exactly the kind of incidental coupling this shared foundation module exists
# to avoid. Output is unaffected: this only moves where the function/constant live.
SHAPES: list[str] = ["disc", "diamond", "square", "triangle"]


def marker_path(shape: str, x: float, y: float, r: float) -> str:
    """lib/charts-cat.ts:99-110 markerPath()."""
    a, b, cc, d = (round1(v) for v in (x - r, x + r, y - r, y + r))
    if shape == "diamond":
        return f"M{js_num(round1(x))},{js_num(cc)} L{js_num(b)},{js_num(round1(y))} L{js_num(round1(x))},{js_num(d)} L{js_num(a)},{js_num(round1(y))} Z"
    if shape == "square":
        return f"M{js_num(a)},{js_num(cc)} H{js_num(b)} V{js_num(d)} H{js_num(a)} Z"
    if shape == "triangle":
        return f"M{js_num(round1(x))},{js_num(cc)} L{js_num(b)},{js_num(d)} L{js_num(a)},{js_num(d)} Z"
    return f"M{js_num(a)},{js_num(round1(y))} a{js_num(r)},{js_num(r)} 0 1,0 {js_num(round1(2 * r))},0 a{js_num(r)},{js_num(r)} 0 1,0 {js_num(round1(-2 * r))},0 Z"


def _to_precision(n: float, p: int) -> float:
    """JS `parseFloat(n.toPrecision(p))`."""
    if n == 0:
        return 0.0
    d = p - 1 - math.floor(math.log10(abs(n)))
    factor = 10.0**d
    rounded = math.floor(abs(n) * factor + 0.5) / factor
    return rounded if n >= 0 else -rounded


_COMMA_RE = re.compile(r"(?<=\d)(?=(?:\d{3})+$)")


def num_text(n: float) -> str:
    """lib/charts-base.ts:58-64 numText()."""
    if not math.isfinite(n):
        return str(n)
    s = js_num(_to_precision(n, 12))
    neg = s.startswith("-")
    body = s[1:] if neg else s
    int_part, _, dec = body.partition(".")
    int_part = _COMMA_RE.sub(",", int_part)
    return f"{'-' if neg else ''}{int_part}{'.' + dec if dec else ''}"


def signed_text(n: float) -> str:
    """lib/charts-base.ts:66 signedText()."""
    return f"{'' if n < 0 else '+'}{num_text(n)}"


def decimals_in(n: float) -> int:
    """lib/charts-base.ts:67 decimalsIn()."""
    s = js_num(_to_precision(n, 12))
    if "e" in s.lower():
        return 6
    i = s.find(".")
    return 0 if i < 0 else len(s) - i - 1


def nice_near(raw: float) -> float:
    """lib/qc.ts:22-26 niceNear()."""
    if not (raw > 0):
        return 1.0
    mag = 10 ** math.floor(math.log10(raw))
    f = raw / mag
    return mag * (1 if f < 1.5 else 2 if f < 3.5 else 5 if f < 7.5 else 10)


def nice_up(raw: float) -> float:
    """lib/qc.ts:28-32 niceUp()."""
    if not (raw > 0):
        return 1.0
    mag = 10 ** math.floor(math.log10(raw))
    f = raw / mag
    return mag * (1 if f <= 1 else 2 if f <= 2 else 5 if f <= 5 else 10)


def nice_scale(lo: float, hi: float, want: int = 5) -> dict:
    """lib/charts-base.ts:70-77 niceScale()."""
    if not (hi > lo):
        hi = lo + 1
    step = nice_near((hi - lo) / want)
    min_v = math.floor(lo / step + 1e-9) * step
    max_v = max(math.ceil(hi / step - 1e-9) * step, min_v + step)
    ticks = []
    i = 0
    while i <= round((max_v - min_v) / step) and i < 100:
        ticks.append(_to_precision(min_v + i * step, 12))
        i += 1
    return {"min": _to_precision(min_v, 12), "max": _to_precision(max_v, 12), "step": step, "ticks": ticks}


_MAX_HISTOGRAM_CLASSES = 60


def exact_text(n: float) -> str:
    """lib/qc.ts:9 exact()."""
    return js_num(_to_precision(n, 12))


def histogram_bins(values: list[float], bins: int | None = None, width: float | None = None) -> dict:
    """lib/qc.ts:73-87 histogramBins() (only the {bins?, width?} overload; `include` is not
    used by any of this port's callers and is not ported). Shared by distplot.py and
    multiplot.py — hoisted here rather than left in one of them, since neither chart kind
    owns histogram binning any more than the other."""
    dlo, dhi = min(values), max(values)
    want = bins if bins is not None else math.ceil(math.log2(len(values))) + 1
    w = width if width is not None else nice_near((dhi - dlo or abs(dhi) or 1) / want)
    lo, hi = dlo, dhi
    start = math.floor(lo / w + 1e-9) * w
    n = max(1, math.ceil((hi - start) / w - 1e-9))
    if n > _MAX_HISTOGRAM_CLASSES:
        raise ValueError(f"histogram(): {n} classes of width {exact_text(w)} (at most {_MAX_HISTOGRAM_CLASSES}): use a wider width, fewer bins, or limits closer to the data")
    if start + n * w <= hi - 1e-9:
        n += 1
    edges = [_to_precision(start + i * w, 12) for i in range(n + 1)]
    counts = [0.0] * n
    for v in values:
        k = min(n - 1, max(0, math.floor((v - start) / w + 1e-9)))
        counts[k] += 1
    return {"edges": edges, "counts": counts, "width": w}


def check_domain(who: str, domain: tuple[float, float] | None) -> tuple[float, float] | None:
    """lib/charts-base.ts:80-84 checkDomain()."""
    if domain is None:
        return None
    if len(domain) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in domain) or not domain[0] < domain[1]:
        fail(who, f"domain must be [lo, hi] with finite numbers and lo < hi (got {list(domain)})")
    return (domain[0], domain[1])


def check_inset(who: str, inset: tuple[float, float] | None) -> tuple[float, float] | None:
    """lib/charts-base.ts:86-90 checkInset()."""
    if inset is None:
        return None
    if len(inset) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in inset):
        fail(who, f"plotInset must be [left, right], two numbers >= 0 (got {list(inset)})")
    return (inset[0], inset[1])


def check_range(who: str, opts: dict, key: str) -> tuple[float, float] | None:
    """The `xRange`/`yRange` validator every seaborn-style chart's resolve*() repeats
    verbatim (lib/charts-dist.ts's / lib/charts-multi.ts's / lib/charts-reg.ts's inline
    `range()`/`rng()` closures): opts[key] must be [min, max] with min < max, or left out."""
    v = opts.get(key)
    if v is None:
        return None
    if not isinstance(v, (list, tuple)) or len(v) != 2 or not all(isinstance(q, (int, float)) and math.isfinite(q) for q in v) or not v[0] < v[1]:
        fail(who, f"{key} must be [min, max] with min < max (got {json.dumps(list(v)) if isinstance(v, (list, tuple)) else v})")
    return (v[0], v[1])


def inset_or_need(who: str, inset: tuple[float, float] | None, need_left: float, need_right: float) -> tuple[float, float]:
    """lib/charts-base.ts:92-96 insetOrNeed()."""
    if inset is None:
        return (need_left, need_right)
    if inset[0] < need_left - 0.5 or inset[1] < need_right - 0.5:
        fail(
            who,
            f"plotInset [{js_round(inset[0])}, {js_round(inset[1])}] leaves too little room for the labels: "
            f"this chart needs at least [{math.ceil(need_left)}, {math.ceil(need_right)}] (write the largest of the charts you want to line up)",
        )
    return (inset[0], inset[1])


def value_scale(who: str, lo: float, hi: float, domain: tuple[float, float] | None = None) -> dict:
    """lib/charts-base.ts:97-102 valueScale()."""
    if domain is None:
        return nice_scale(lo, hi)
    if lo < domain[0] - 1e-9 or hi > domain[1] + 1e-9:
        fail(who, f"domain [{num_text(domain[0])}, {num_text(domain[1])}] is smaller than the data [{num_text(lo)}, {num_text(hi)}] (widen the domain)")
    return nice_scale(domain[0], domain[1])


def thin_ticks(ticks: list[dict], px, size, gap: float = 10) -> list[dict]:
    """lib/charts-base.ts:104-110 thinTicks()."""
    if len(ticks) < 2:
        return list(ticks)
    pitch = abs(px(ticks[1]["v"]) - px(ticks[0]["v"]))
    need = max(size(t) for t in ticks) + gap
    k = max(1, math.ceil(need / max(1, pitch)))
    zero = max(0, next((i for i, t in enumerate(ticks) if t["v"] == 0), -1))
    return [t for i, t in enumerate(ticks) if ((i - zero) % k + k) % k == 0]


def size_of(label_role: str | None, roles: dict) -> float:
    """lib/charts-base.ts:193 sizeOf()."""
    return roles[label_role or "note"]


def common_chart_opts(who: str, *, id: str | None = None, width: float | None = None, height: float | None = None, label_role: str | None = None, reveal: int | None = None, until: int | None = None) -> dict:
    """lib/charts-dsl.ts:41-48 common() — the band fields every chart kind's *Band()
    constructor shares (id/width/height/labelRole/reveal/until), as kwargs ready to splat
    into a ChartBand (see below) alongside that caller's own kind/spec/alt. `scope`
    (spotlight) is not ported, consistent with the rest of this port."""
    if label_role is not None and label_role not in ("note", "banner", "stat"):
        fail(who, f"labelRole must be note, banner or stat (got {label_role})")
    for k, v in (("width", width), ("height", height)):
        if v is not None and not (math.isfinite(v) and v > 0):
            fail(who, f"{k} must be a number > 0 (got {v})")
    out: dict = {}
    if id is not None:
        out["id"] = id
    if width is not None:
        out["width"] = width
    if height is not None:
        out["height"] = height
    if label_role is not None:
        out["label_role"] = label_role
    if reveal is not None:
        out["reveal"] = reveal
    if until is not None:
        out["until"] = until
    return out


@dataclass(frozen=True)
class ChartBand:
    """lib/charts-dsl.ts's shared ChartBand envelope: every chart kind's own *_band()
    function (heatmap_band(), sankey_band(), ..., pert_band(), causal_band(), ...) builds one
    of these — common_chart_opts() already validates id/width/height/labelRole before this is
    constructed, so this dataclass adds no further checking of its own, just the fields every
    kind shares, plus its own `kind` (what layout_chart() dispatches on) and `spec` (that
    kind's own shape, still a plain dict — see each file's resolve_X() for it).

    Not a JSON boundary: layout_chart()'s *return* value (LaidOutChart) is the one that
    crosses into Node's golden CLI as JSON (see charts.py's render_chart() for why that one
    stays a dict); a ChartBand never leaves the Python process.
    """

    kind: str
    spec: dict
    alt: str
    id: str | None = None
    width: float | None = None
    height: float | None = None
    label_role: str | None = None
    reveal: int | None = None
    until: int | None = None


class Canvas:
    """lib/charts-base.ts:114-190 Canvas."""

    def __init__(self, x: float, y: float, w: float, h: float, size: float, width_of, mode: str) -> None:
        self.x, self.y, self.w, self.h, self.size, self.width_of, self.mode = x, y, w, h, size, width_of, mode
        self.items: list[dict] = []
        self.boxes: list[dict] = []
        self.solids: list[dict] = []
        self.segs: list[dict] = []
        self.anchors: list[dict] = []
        self.omitted: list[str] = []
        self.edges: list[dict] = []
        self.marks: list[dict] = []

    def tw(self, s: str, bold: bool = False) -> float:
        return text_width(self.width_of, s, self.size, 700 if bold else 400)

    def box_of(self, s: str, x: float, base: float, anchor: str, bold: bool = False) -> dict:
        w = self.tw(s, bold)
        return {"x": (x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)), "y": base - self.size, "w": w, "h": self.size + 4}

    def mid(self, cy: float) -> float:
        return js_round(cy + self.size * 0.36)

    def rect(self, x: float, y: float, w: float, h: float, o: dict) -> int:
        item = {"k": "rect", "x": x, "y": y, "w": w, "h": h, "fill": o["fill"]}
        if o.get("op") is not None:
            item["op"] = o["op"]
        if o.get("stroke"):
            item["stroke"] = o["stroke"]
        if o.get("sw"):
            item["sw"] = o["sw"]
        if o.get("dash"):
            item["dash"] = o["dash"]
        if o.get("of"):
            item["of"] = o["of"]
        self.items.append(item)
        if o.get("id"):
            self.anchors.append({"id": o["id"], "x": x, "y": y, "w": w, "h": h})
        if o.get("solid") is not None:
            box = {"x": x, "y": y, "w": w, "h": h, "label": o["solid"]}
            if o.get("id"):
                box["id"] = o["id"]
            self.solids.append(box)
            return len(self.solids) - 1
        return -1

    def path(self, d: str, o: dict) -> None:
        item = {"k": "path", "d": d, "fill": o["fill"]}
        if o.get("op") is not None:
            item["op"] = o["op"]
        if o.get("stroke"):
            item["stroke"] = o["stroke"]
        if o.get("sw"):
            item["sw"] = o["sw"]
        if o.get("dash"):
            item["dash"] = o["dash"]
        if o.get("of"):
            item["of"] = o["of"]
        if o.get("soft"):
            item["soft"] = True
        self.items.append(item)

    def line(self, x1: float, y1: float, x2: float, y2: float, o: dict) -> None:
        self.path(f"M{js_num(round1(x1))},{js_num(round1(y1))} L{js_num(round1(x2))},{js_num(round1(y2))}", {"fill": "none", "stroke": o["stroke"], "sw": o.get("sw", 2), "dash": o.get("dash"), "of": o.get("of"), "soft": o.get("soft")})
        if o.get("avoid"):
            self.segs.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    def icon(self, glyph, name: str, x: float, y: float, size: float, fill: str, of: str | None = None) -> None:
        item = {"k": "icon", "name": name, "glyph": glyph, "x": x, "y": y, "size": size, "fill": fill}
        if of:
            item["of"] = of
        self.items.append(item)

    def text(self, s: str, x: float, base: float, anchor: str, fill: str, o: dict | None = None) -> dict:
        o = o or {}
        x, base = js_round(x), js_round(base)
        if o.get("plate"):
            p = self.box_of(s, x, base, anchor, o.get("bold", False))
            self.items.append({"k": "rect", "x": p["x"] - 2, "y": p["y"], "w": p["w"] + 4, "h": p["h"], "fill": "bg"})
        item = {"k": "text", "s": s, "x": x, "y": base, "anchor": anchor, "fill": fill, "size": self.size}
        if o.get("bold"):
            item["bold"] = True
        if o.get("of"):
            item["of"] = o["of"]
        self.items.append(item)
        b = {"label": s, **self.box_of(s, x, base, anchor, o.get("bold", False))}
        if o.get("on") is not None:
            b["on"] = o["on"]
        if o.get("plate"):
            b["plate"] = True
        if o.get("host") is not None and o["host"] >= 0:
            b["host"] = o["host"]
        if o.get("of"):
            b["of"] = o["of"]
        self.boxes.append(b)
        return b

    def free(self, b: dict, host: int = -1, margin: float = 0, plated: bool = False) -> bool:
        if b["x"] < self.x - 0.5 + margin or b["x"] + b["w"] > self.x + self.w + 0.5 - margin or b["y"] < self.y - 0.5 + margin or b["y"] + b["h"] > self.y + self.h + 0.5 - margin:
            return False
        if any(overlaps(b, o) for o in self.boxes):
            return False
        if any(overlaps(b, s) for i, s in enumerate(self.solids) if i != host):
            return False
        if any(overlaps(b, m) for m in self.marks):
            return False
        return plated or not any(seg_hits_rect(sg, {"x": b["x"] - 1, "y": b["y"], "w": b["w"] + 2, "h": b["h"]}) for sg in self.segs)

    def place(self, s: str, cands: list[dict], fill: str, o: dict | None = None) -> dict | None:
        o = o or {}
        for c in cands:
            if self.free(self.box_of(s, js_round(c["x"]), js_round(c["y"]), c["anchor"], o.get("bold", False)), o.get("host", -1), 0, bool(o.get("plate"))):
                return self.text(s, c["x"], c["y"], c["anchor"], fill, o)
        return None

    def wrap(self, s: str, max_w: float, bold: bool = False) -> list[str]:
        return wrap_atoms(split_atoms(s), max_width=max(20, max_w), atom_width=lambda a: text_width(self.width_of, a, self.size, 700 if bold else 400), mode=self.mode)

    def lines(self, ls: list[str], x: float, base: float, anchor: str, fill: str, o: dict | None = None) -> None:
        o = o or {}
        for i, l in enumerate(ls):
            self.text(l, x, base + i * js_round(self.size * 1.25), anchor, fill, o)

    def line_h(self) -> float:
        return js_round(self.size * 1.25)

    def done(self) -> dict:
        out = {"items": self.items, "boxes": self.boxes, "solids": self.solids, "segs": self.segs, "anchors": self.anchors, "omitted": self.omitted, "h": self.h}
        if self.edges:
            out["edges"] = self.edges
        return out
