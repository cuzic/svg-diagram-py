"""1:1 port of lib/wordart-look.ts — presets, the resolved look, and the layers a placed
wordart is painted in. Pure.

`legibilityProblem` (a lint-time contrast check, not used at render/layout time) is not
ported — out of scope, same as other lint/diagnostics features this port skips.

Golden master: lib/wordart-look.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .emit_common import js_round
from .tokens import PALETTE, color_of

ART_TONES: frozenset[str] = frozenset({"text", "accent", "muted", "danger", "bg", "soft"})
ART_TONE_NAMES: list[str] = ["text", "accent", "muted", "danger", "bg", "soft"]


def is_art_tone(v) -> bool:
    return v in ART_TONES


WEIGHT_OF: dict[str, int] = {"normal": 400, "bold": 700}
OUTLINE_REL = 0.06
SHADOW_REL = 0.06
GLOW_REL = 0.25
EXTRUDE_REL = 0.1
BEVEL_REL = 0.03
REFLECTION_GAP_REL = 0.05
REFLECTION_SHARE = 0.6
GLOW_RINGS = 4
EXTRUDE_MAX_STEPS = 12

# lib/wordart-look.ts:32-46 PRESETS
PRESETS: dict[str, dict] = {
    "plain": {"weight": 400, "tone": "text"},
    "bold": {"weight": 700, "tone": "text"},
    "outline": {"weight": 700, "tone": "bg", "outline": [{"tone": "text", "share": OUTLINE_REL}]},
    "shadow": {"weight": 700, "tone": "accent", "shadow": {"tone": "muted"}},
    "sticker": {"weight": 700, "tone": "accent", "outline": [{"tone": "bg", "share": 0.06}, {"tone": "text", "share": 0.05}], "shadow": {"tone": "muted"}},
    "glow": {"weight": 700, "tone": "bg", "outline": [{"tone": "accent", "share": 0.04}], "glow": {"tone": "accent"}},
    "emboss": {"weight": 700, "tone": "soft", "outline": [{"tone": "accent", "share": 0.03}], "bevel": True},
    "3d": {"weight": 700, "tone": "accent", "extrude": {"tone": "text"}},
    "gradient": {"weight": 700, "tone": "accent", "gradient": {"from": "accent", "to": "text"}},
    "reflect": {"weight": 700, "tone": "accent", "reflection": {}},
}


def as_list(o) -> list | None:
    """lib/wordart-look.ts:48 asList()."""
    if o is None or o is False:
        return None
    if o is True:
        return [{}]
    if isinstance(o, list):
        return o
    return [o]


def _spec_of(v, preset):
    """lib/wordart-look.ts:49 specOf()."""
    if v is False:
        return None
    if v is None:
        return preset
    if v is True:
        return {}
    return v


def size_of(size, roles: dict) -> float:
    """lib/wordart-look.ts:51 sizeOf()."""
    if size is None:
        return roles["display"]
    if isinstance(size, (int, float)):
        return size
    return roles[size]


def resolve_look(opts: dict, size: float) -> dict:
    """lib/wordart-look.ts:54-85 resolveLook()."""
    p = PRESETS[opts.get("style") or "bold"]

    def px(share: float) -> float:
        return max(1.5, math.ceil(size * share * 2) / 2)

    opt_outline = opts.get("outline")
    if opt_outline is False:
        outline = []
    elif opt_outline is None:
        outline = [{"tone": o["tone"], "width": px(o["share"])} for o in p.get("outline", [])]
    else:
        lst = as_list(opt_outline) or []
        outline = [{"tone": o.get("tone") if o.get("tone") is not None else "text", "width": o.get("width") if o.get("width") is not None else px(OUTLINE_REL)} for o in lst]

    sh = _spec_of(opts.get("shadow"), p.get("shadow"))
    gl = _spec_of(opts.get("glow"), p.get("glow"))
    ex = _spec_of(opts.get("extrude"), p.get("extrude"))
    rf = _spec_of(opts.get("reflection"), p.get("reflection"))
    bevel = p.get("bevel") if opts.get("bevel") is None else opts.get("bevel")

    shift = max(2, js_round(size * SHADOW_REL))
    depth = (ex.get("depth") if ex else None)
    if depth is None:
        depth = max(3, js_round(size * EXTRUDE_REL))
    grad = opts.get("gradient")
    if grad is None:
        grad = p.get("gradient") if opts.get("tone") is None else None
    rot = opts.get("rotate", 0)
    flip = opts.get("flip")
    fill = opts.get("tone") if opts.get("tone") is not None else p.get("tone")

    def apart(tone: str, dflt: str) -> str:
        if tone == dflt:
            return "muted" if dflt == "text" else "text"
        return dflt

    look: dict = {
        "size": size,
        "weight": WEIGHT_OF[opts["weight"]] if opts.get("weight") else p["weight"],
        "font": opts.get("font", "sans"),
        "fill": fill,
    }
    if grad is not None:
        look["gradient"] = {"from": grad["from"], "to": grad["to"], "angle": grad.get("angle", 90)}
    look["outlines"] = outline
    # NB: sh/gl/ex/rf are spec dicts that may legitimately be `{}` (e.g. `reflection: true` ->
    # `_spec_of` returns {}) meaning "use every default" — `{}` is truthy in JS but falsy in
    # Python, so these must be `is not None` checks, not bare truthiness checks.
    if sh is not None:
        look["shadow"] = {"tone": sh.get("tone") if sh.get("tone") is not None else apart(fill, "muted"), "dx": sh.get("dx") if sh.get("dx") is not None else shift, "dy": sh.get("dy") if sh.get("dy") is not None else shift}
    if gl is not None:
        look["glow"] = {"tone": gl.get("tone") if gl.get("tone") is not None else "accent", "radius": gl.get("radius") if gl.get("radius") is not None else max(3, js_round(size * GLOW_REL))}
    if bevel:
        look["bevel"] = {"size": max(1, js_round(size * BEVEL_REL))}
    if ex is not None:
        look["extrude"] = {"tone": ex.get("tone") if ex.get("tone") is not None else apart(fill, "text"), "dx": js_round(depth * 0.7), "dy": js_round(depth * 0.7)}
    if rf is not None:
        look["reflection"] = {"opacity": rf.get("opacity") if rf.get("opacity") is not None else 0.3, "gap": rf.get("gap") if rf.get("gap") is not None else max(2, js_round(size * REFLECTION_GAP_REL))}
    if opts.get("plate"):
        look["plate"] = opts["plate"]
    look["spacing"] = opts.get("spacing", 0)
    if opts.get("arc"):
        look["arc"] = opts["arc"]
    look["rotate"] = rot
    look["flipH"] = flip in ("horizontal", "both")
    look["flipV"] = flip in ("vertical", "both")
    return look


def ink_reach(look: dict) -> dict:
    """lib/wordart-look.ts:88-93 inkReach()."""
    o = sum(x["width"] for x in look["outlines"]) + look.get("glow", {}).get("radius", 0) + look.get("bevel", {}).get("size", 0)
    dx = [look.get("shadow", {}).get("dx", 0), look.get("extrude", {}).get("dx", 0)]
    dy = [look.get("shadow", {}).get("dy", 0), look.get("extrude", {}).get("dy", 0)]
    return {
        "left": o + max([0] + [-v for v in dx]),
        "top": o + max([0] + [-v for v in dy]),
        "right": o + max([0] + dx),
        "bottom": o + max([0] + dy),
    }


def min_rim(size: float) -> float:
    """lib/wordart-look.ts:96 minRim()."""
    return max(1, size * 0.03)


def _rgb_of(hex_color: str) -> list[int]:
    return [int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)]


def _hex_of(c: list[float]) -> str:
    return "#" + "".join(f"{js_round(v):02x}" for v in c)


def gradient_steps(frm: str, to: str, n: int = 10) -> list[str]:
    """lib/wordart-look.ts:101-104 gradientSteps()."""
    a, b = _rgb_of(frm), _rgb_of(to)
    return [_hex_of([v + (b[k] - v) * i / n for k, v in enumerate(a)]) for i in range(n + 1)]


def _to_base36(n: int) -> str:
    if n == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append(digits[r])
    return "".join(reversed(out))


def _hash36(s: str) -> str:
    """A stable, Python-only djb2-style hash (not byte-matching Node's Math.imul/JSON.stringify
    hash — this id only needs to be unique within one rendered SVG, and golden tests exclude
    the `uid`/`uid`-derived fields from their comparison for exactly this reason)."""
    h = 5381
    for ch in s:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return _to_base36(h)


def gradient_id(art: dict, day) -> str:
    """lib/wordart-look.ts:155-160 gradientId() — see _hash36()'s docstring for the fidelity tradeoff."""
    g = art["look"].get("gradient")
    ends = (color_of(g["from"], day) + color_of(g["to"], day)) if g else ""
    return f"{art['uid']}-g{_hash36(ends)}"


def gradient_of(art: dict, day) -> dict | None:
    """lib/wordart-look.ts:162-167 gradientOf()."""
    g = art["look"].get("gradient")
    if not g:
        return None
    a = g["angle"] * math.pi / 180
    rect = art["local"]
    x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
    cx, cy = x + w / 2, y + h / 2
    length = (abs(w * math.cos(a)) + abs(h * math.sin(a))) / 2
    return {
        "id": gradient_id(art, day),
        "x1": cx - length * math.cos(a),
        "y1": cy - length * math.sin(a),
        "x2": cx + length * math.cos(a),
        "y2": cy + length * math.sin(a),
        "from": color_of(g["from"], day),
        "to": color_of(g["to"], day),
    }


def paint_layers(art: dict, day, dim: bool = False) -> list[dict]:
    """lib/wordart-look.ts:170-191 paintLayers()."""
    look = art["look"]

    def col(t: str) -> str:
        return color_of(t, day)

    if dim:
        hollow_no_grad = look["fill"] == "none" and not look.get("gradient")
        layer = {"fill": "none" if hollow_no_grad else PALETTE["muted"], "dx": 0, "dy": 0, "hidden": False, "text": True}
        if hollow_no_grad and look["outlines"]:
            layer["stroke"] = PALETTE["muted"]
            layer["sw"] = look["outlines"][0]["width"]
        return [layer]

    layers: list[dict] = []
    total = sum(o["width"] for o in look["outlines"])
    inner = look["outlines"][0] if look["outlines"] else None
    fill = f'url(#{gradient_id(art, day)})' if look.get("gradient") else ("none" if look["fill"] == "none" else col(look["fill"]))
    hollow = fill == "none"

    def silhouette(tone: str, width: float, extra: dict | None = None) -> dict:
        layer = {"fill": col(tone), "dx": 0, "dy": 0, "hidden": True}
        if width > 0:
            layer["stroke"] = col(tone)
            layer["sw"] = 2 * width
        layer.update(extra or {})
        return layer

    own: dict = {}
    if inner:
        own["stroke"] = col(inner["tone"])
        own["sw"] = inner["width"] if hollow else 2 * inner["width"]

    if look.get("reflection"):
        layers.append({"fill": fill, **own, "dx": 0, "dy": 0, "opacity": look["reflection"]["opacity"], "hidden": True, "mirror": True})
    if look.get("shadow"):
        layers.append(silhouette(look["shadow"]["tone"], total, {"dx": look["shadow"]["dx"], "dy": look["shadow"]["dy"]}))
    if look.get("glow"):
        for k in range(GLOW_RINGS, 0, -1):
            layers.append(silhouette(look["glow"]["tone"], total + look["glow"]["radius"] * k / GLOW_RINGS, {"opacity": 0.12}))
    if look.get("extrude"):
        n = min(EXTRUDE_MAX_STEPS, max(1, math.ceil(max(look["extrude"]["dx"], look["extrude"]["dy"]))))
        for i in range(n, 0, -1):
            layers.append(silhouette(look["extrude"]["tone"], total, {"dx": look["extrude"]["dx"] * i / n, "dy": look["extrude"]["dy"] * i / n}))

    reach = total
    for o in list(reversed(look["outlines"]))[:-1]:
        layers.append(silhouette(o["tone"], reach))
        reach -= o["width"]
    if look.get("bevel"):
        b = look["bevel"]["size"]
        layers.append(silhouette("text", total, {"dx": b, "dy": b, "opacity": 0.45}))
        layers.append(silhouette("bg", total, {"dx": -b, "dy": -b, "opacity": 0.8}))
    layers.append({"fill": fill, **own, "dx": 0, "dy": 0, "hidden": False, "text": True})
    return layers


def figure_transform(art: dict) -> str | None:
    """lib/wordart-look.ts:194-199 figureTransform()."""
    from .emit_common import js_num

    look = art["look"]
    cx, cy = art["x"] + art["w"] / 2, art["y"] + art["h"] / 2

    def n(v: float) -> float:
        return js_round(v * 100) / 100

    flip = ""
    if look["flipH"] or look["flipV"]:
        flip = f' translate({js_num(n(cx))} {js_num(n(cy))}) scale({-1 if look["flipH"] else 1} {-1 if look["flipV"] else 1}) translate({js_num(n(-cx))} {js_num(n(-cy))})'
    turn = f'rotate({js_num(n(look["rotate"]))} {js_num(n(cx))} {js_num(n(cy))})' if look["rotate"] else ""
    result = f"{turn}{flip}".strip()
    return result or None
