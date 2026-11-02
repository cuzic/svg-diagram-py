"""Scoped port of lib/fit-width.ts's fitLayout() — covering only what this port's two
current users (bowtie.py, fta.py) exercise: a single direction (neither ever alternates
it — `noDir: true`, no `alt`), no folding (`foldable` unset), no `autoWidth` grid, and no
diagram({keepWords}) floor retry (this port does not support that diagram option at all —
see tree.py's identical scope note on this same Node module).

The NARROWING width cascade and the `fitApplied` bookkeeping (what/from/to/mode/wasW/nowW)
ARE ported faithfully, since they are part of each caller's own byte-compared output.

Golden master: lib/fit-width.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .emit_common import js_round

NARROWING = [200, 160, 130, 110]
WIDEST = NARROWING[0]


def fit_layout(*, who: str, w: float, max_node_w: float | None, mode: str, build, fix: str) -> dict:
    """lib/fit-width.ts:161-235 fitLayout(), scoped (see module docstring). `build(max_w,
    floor)` always receives `floor=False` (no keepWords support). Returns {"result":
    build()'s return value, "applied": a (possibly empty) list of FitApplied-shaped dicts}.
    """
    widths = [max_node_w] if max_node_w is not None else NARROWING
    from0 = widths[0]
    tried: list[dict] = []
    for mw in widths:
        result = build(mw, False)
        width = result["size"]["w"]
        tw, th = math.ceil(width), math.ceil(result["size"]["h"])
        tried.append({"w": tw, "h": th})
        if width <= w + 0.5:
            applied = []
            if mw != from0:
                applied = [{"what": "maxNodeW", "from": from0, "to": mw, "mode": mode, "wasW": tried[0]["w"], "nowW": tw}]
            return {"result": result, "applied": applied}
    tried_desc = "; ".join(f"maxNodeW {t['w']}px wide, {t['h']}px tall" for t in tried)
    raise ValueError(f"{who}: the figure does not fit {js_round(w)}px.\n  tried: {tried_desc}\n  fix: {fix}")
