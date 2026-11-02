"""1:1 port of lib/charts.ts's layoutChart() (the one dispatcher every chart kind's
layout_X() goes through) and lib/charts-emit.ts's renderChart() (the one render function
every chart kind's LaidOutChartPart items go through — ported once here, reused by every
future chart kind).

Spotlight dim/stage filtering is not ported: this port's chart bands never set
`dim`/`dimIds`/`reveal` stages, so every item is always visible and never dimmed, same scope
decision as flow_shapes.py's render_flow_shape(). Icon items (Canvas.icon()) need the icon
registry, which box({icon}) already left out of this port's scope — raises if one appears.

Golden master: lib/charts.ts + lib/charts-emit.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from .bubble import layout_bubble
from .butterfly import layout_butterfly
from .catplot import layout_cat
from .combo import layout_combo
from .distplot import layout_dist
from .multiplot import layout_multi
from .regplot import layout_reg
from .charts_base import size_of
from .emit_common import emoji_span, js_num, js_round
from .harvey import layout_harvey
from .heatmap import layout_heatmap
from .radar import layout_radar
from .sankey import layout_sankey
from .stacked import layout_stacked
from .tokens import PALETTE, color_of
from .tornado import layout_tornado
from .treemap import layout_treemap
from .waterfall import layout_waterfall


def layout_chart(band: dict, x: float, y: float, w: float, width_of, roles: dict, wrap: str = "phrase") -> dict:
    """lib/charts.ts:96-124 layoutChart()."""
    size = size_of(band.get("labelRole"), roles)
    width = band.get("width") if band.get("width") is not None else w
    width = min(w, width)
    left = x + (w - width) / 2
    g = {"x": left, "y": y, "w": width, "height": band.get("height"), "size": size, "widthOf": width_of, "wrap": wrap}
    kind = band["kind"]
    if kind == "heatmap":
        part = layout_heatmap(band["spec"], g)
    elif kind == "sankey":
        part = layout_sankey(band["spec"], g)
    elif kind == "radar":
        part = layout_radar(band["spec"], g)
    elif kind == "treemap":
        part = layout_treemap(band["spec"], g)
    elif kind == "waterfall":
        part = layout_waterfall(band["spec"], g)
    elif kind == "stacked":
        part = layout_stacked(band["spec"], g)
    elif kind == "tornado":
        part = layout_tornado(band["spec"], g)
    elif kind == "butterfly":
        part = layout_butterfly(band["spec"], g)
    elif kind == "harvey":
        part = layout_harvey(band["spec"], g)
    elif kind == "bubble":
        part = layout_bubble(band["spec"], g)
    elif kind == "combo":
        part = layout_combo(band["spec"], g)
    elif kind == "catplot":
        part = layout_cat(band["spec"], g)
    elif kind == "distplot":
        part = layout_dist(band["spec"], g)
    elif kind == "multiplot":
        part = layout_multi(band["spec"], g)
    elif kind == "regplot":
        part = layout_reg(band["spec"], g)
    else:
        raise NotImplementedError(f"layout_chart(): {kind!r} is not supported by this port yet")
    result = {"type": "chart", "kind": kind, "alt": band["alt"], "size": size, "x": left, "y": y, "w": width, **part}
    if band.get("id") is not None:
        result["id"] = band["id"]
    if band.get("reveal") is not None:
        result["reveal"] = band["reveal"]
    if band.get("until") is not None:
        result["until"] = band["until"]
    return result


def _r2(n: float) -> float:
    return js_round(n * 100) / 100


def render_chart(b: dict, day: int | str = 1) -> str:
    """lib/charts-emit.ts:10-47 renderChart()."""

    def col(k: str) -> str:
        return color_of(k, day)

    out: list[str] = []
    for it in b["items"]:
        k = it["k"]
        if k == "rect":
            x, y = _r2(it["x"]), _r2(it["y"])
            right, bottom = _r2(it["x"] + it["w"]), _r2(it["y"] + it["h"])
            d = f"M{js_num(x)},{js_num(y)} H{js_num(right)} V{js_num(bottom)} H{js_num(x)} Z"
            fill = "none" if it["fill"] == "none" else col(it["fill"])
            op = f' fill-opacity="{js_num(it["op"])}"' if it.get("op") is not None and it["fill"] != "none" else ""
            stroke = ""
            if it.get("stroke"):
                dash = f' stroke-dasharray="{it["dash"]}"' if it.get("dash") else ""
                stroke = f' stroke="{col(it["stroke"])}" stroke-width="{js_num(it.get("sw") or 2)}"{dash}'
            if op:
                out.append(f'<path d="{d}" fill="{PALETTE["bg"]}"/>')
            out.append(f'<path d="{d}" fill="{fill}"{op}{stroke}/>')
        elif k == "path":
            fill = "none" if it["fill"] == "none" else col(it["fill"])
            op = f' fill-opacity="{js_num(it["op"])}"' if it.get("op") is not None and it["fill"] != "none" else ""
            stroke = ""
            if it.get("stroke"):
                dash = f' stroke-dasharray="{it["dash"]}"' if it.get("dash") else ""
                stroke = f' stroke="{col(it["stroke"])}" stroke-width="{js_num(it.get("sw") or 2)}" stroke-linejoin="round"{dash}'
            out.append(f'<path d="{it["d"]}" fill="{fill}"{op}{stroke}/>')
        elif k == "icon":
            raise NotImplementedError("render_chart(): icon items need the icon registry, out of scope (see box({icon})'s scope note)")
        else:
            anchor = "" if it["anchor"] == "start" else f' text-anchor="{it["anchor"]}"'
            weight = ' font-weight="700"' if it.get("bold") else ""
            out.append(f'<text x="{it["x"]}" y="{it["y"]}"{anchor} font-size="{it["size"]}"{weight} fill="{col(it["fill"])}">{emoji_span(it["s"])}</text>')
    return "\n  ".join(out)
