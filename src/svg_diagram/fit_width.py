"""1:1 port of lib/fit-width.ts: fitWidth/fitLayout/planFit (the general direction+width
search engine that wraps layered_route.py's layered_attempt(), used by classDiagram() and,
later, stateDiagram()/causeTree()) plus the small pure helpers fitFailure/widerThan/
describeApplied/withWidths, and lib/fit-split.ts's splitByHeight/splitWidest (what to say
when a figure fits neither the width nor the height, ADR 0019 D3).

`narrow_cascade_fit()` below is a SEPARATE, narrower function — not part of lib/fit-width.ts's
public surface, named here only for this port's own convenience — covering just what this
port's two first users (bowtie.py, fta.py) exercise: a single direction (neither ever
alternates it — `noDir: true`, no `alt`), no folding, no `autoWidth` grid, and no
diagram({keepWords}) floor retry. It predates this module's full port and was deliberately
kept narrow (see tree.py's identical scope note on fit-width.ts) rather than retrofitted onto
the general engine below, to avoid touching working code without a reason.

Golden master: lib/fit-width.ts + lib/fit-split.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

from collections.abc import Callable

import math

from .emit_common import js_round
from .fit_split import split_by_height, split_widest

NARROWING = [200, 160, 130, 110]
WIDEST = NARROWING[0]


def narrow_cascade_fit(*, who: str, w: float, max_node_w: float | None, mode: str, build, fix: str) -> dict:
    """NOT a port of a single Node function — see the module docstring. `build(max_w,
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


# ---- lib/fit-width.ts's real public surface (classDiagram() and, later, stateDiagram()/causeTree()) ----

SLACK = 0.5
FOLD_SHARES = [1, 0.85, 0.7, 0.55]
AUTO_GRID = [260 - i * 10 for i in range(17)]


def _lex_less(a: dict, b: dict) -> bool:
    return a["crossings"] < b["crossings"] or (a["crossings"] == b["crossings"] and a["bends"] < b["bends"])


def fit_width(w: float, attempts: list[dict], mode: str, height_budget: float | None = None, width_of: Callable[[dict], float] | None = None) -> dict:
    """lib/fit-width.ts:44-61 fitWidth(). Runs the attempts in order. `mode='first'` stops at
    the first that fits `w` (the rest are not run); `'best'` runs them all and keeps the best
    of those that fit `w` and the height budget. `attempts`: [{"label", "run": () -> R,
    "applied"?}]. Returns {"ok": True, "result", "index", "applied", "tried"} or {"ok":
    False, "tried", "results"}."""
    width_of = width_of or (lambda r: r["size"]["w"])
    tried: list[dict] = []
    results: list[dict] = []
    best: dict | None = None
    for index, a in enumerate(attempts):
        result = a["run"]()
        results.append(result)
        width = width_of(result)
        tried.append({"label": a["label"], "w": math.ceil(width), "h": math.ceil(result["size"]["h"]), "fitsWidth": width <= w + SLACK})
        if width > w + SLACK:
            continue
        if height_budget is not None and result["size"]["h"] > height_budget + SLACK:
            continue
        if mode == "first":
            return {"ok": True, "result": result, "index": index, "applied": a.get("applied") or [], "tried": tried}
        if best is None or _lex_less(result["score"], best["result"]["score"]):
            best = {"result": result, "index": index}
    if best is None:
        return {"ok": False, "tried": tried, "results": results}
    return {"ok": True, "result": best["result"], "index": best["index"], "applied": attempts[best["index"]].get("applied") or [], "tried": tried}


def fit_failure(who: str, w: float, tried: list[dict], fix: str, not_tried: list[str] | None = None, height_budget: float | None = None, split: str | None = None) -> str:
    """lib/fit-width.ts:70-78 fitFailure(): the message for a figure no attempt fitted."""
    not_tried = not_tried or []
    too_tall = height_budget is not None and any(t.get("fitsWidth", t["w"] <= w + 0.5) for t in tried)
    if too_tall:
        assert height_budget is not None  # too_tall can only be True when height_budget is not None
        first_line = f"{who}: the figure does not fit {js_round(w)}px wide by {js_round(height_budget)}px tall (every attempt that fits the width is too tall)."
    else:
        first_line = f"{who}: the figure does not fit {js_round(w)}px."
    lines = [first_line]
    if tried:
        lines.append("  tried: " + "; ".join(f'{t["label"]} {t["w"]}px wide, {t["h"]}px tall' for t in tried))
    if not_tried:
        lines.append("  not tried: " + "; ".join(not_tried))
    lines.append(f"  fix: {fix}")
    if split:
        lines.append(f"  split: {split}")
    return "\n".join(lines)


def wider_than(tried: list[dict], margins: float = 0) -> float:
    """lib/fit-width.ts:84-87 widerThan(): a width to suggest in a fix — the narrowest tried
    figure, rounded up to the next 20px and plus the margins the caller gives."""
    least = min(t["w"] for t in tried)
    return math.ceil((least + margins) / 20) * 20


def describe_applied(a: dict) -> str:
    """lib/fit-width.ts:90-95 describeApplied(): one phrase for the `auto-fit-applied` rule."""
    was = "" if a.get("wasW") is None else f"({a['wasW']}→{a.get('nowW', '?')}px)"
    if a["what"] == "fold":
        return f"層 {a['to']} を折り返した{was}"
    if a["what"] == "maxNodeW":
        return f"maxNodeW を {a['from']}→{a['to']} に{'縮めた' if float(a['to']) < float(a['from']) else '広げた'}{was}"
    return f"dir を {a['from']} から {a['to']} に変えた{was}"


def with_widths(applied: list[dict], tried: list[dict], index: int) -> list[dict]:
    """lib/fit-width.ts:98-100 withWidths(): what an attempt changed, with the widths filled
    in — the figure as first tried (`tried[0]`) against the one chosen."""
    return [{**a, "wasW": tried[0]["w"], "nowW": tried[index]["w"]} for a in applied]


def _folded_of(r: dict) -> list[dict]:
    return (r.get("lay") or {}).get("folded") or []


def plan_fit(plan: dict) -> dict:
    """lib/fit-width.ts:159-253 planFit(): lays a figure out in the ways ADR 0010 D1 allows
    and returns the first (or best) that fits `w`, with what was changed to get there (or,
    when none fits, a `failure` callable rather than throwing — a search over several figures
    can set this one aside instead). `plan` (LayoutPlan, see the TS interface for full field
    docs): who/w/start/keepWords/alt?/axisKept?/explicitDir/mode/foldable?/fold?/maxNodeW?/
    autoWidth?/narrow?/noDir?/build(required)/widthOf?/heightBudget?/layoutOf?/best?/
    notTried?/fix?. `build(dir, max_w, floor, fold=None)`."""
    narrow = plan.get("narrow") is not False
    alt = plan.get("alt") if plan.get("alt") != plan["start"] else None
    free = not plan["explicitDir"]
    dirs = [plan["start"], alt] if (free and alt is not None) else [plan["start"]]
    if plan.get("autoWidth"):
        widths = AUTO_GRID
    elif narrow and free and plan.get("maxNodeW") is None:
        widths = NARROWING
    else:
        widths = [plan["maxNodeW"] if plan.get("maxNodeW") is not None else WIDEST]
    width_mode = "auto" if plan.get("autoWidth") else plan["mode"]
    from0 = WIDEST if plan.get("autoWidth") else widths[0]
    floors = [True, False] if plan.get("keepWords") else [False]

    def suffix(floor: bool) -> str:
        return ", words may break" if (plan.get("keepWords") and not floor) else ""

    def narrowing(floor: bool) -> list[dict]:
        out: list[dict] = []
        for mw in widths:
            for d in dirs:
                applied: list[dict] = []
                if d != plan["start"]:
                    applied.append({"what": "dir", "from": plan["start"], "to": d, "mode": plan["mode"]})
                if mw != from0:
                    applied.append({"what": "maxNodeW", "from": from0, "to": mw, "mode": width_mode})
                note = "" if (out or plan.get("autoWidth")) else (" (as written)" if (plan["explicitDir"] or plan.get("maxNodeW") is not None) else " (default)")
                dir_part = "" if plan.get("noDir") else f"dir '{d}'"
                width_part = (f"{', ' if not plan.get('noDir') else ''}maxNodeW {mw}") if narrow else ""
                label = f"{dir_part}{width_part}{note}{suffix(floor)}"
                out.append({"label": label, "run": (lambda d=d, mw=mw, floor=floor: plan["build"](d, mw, floor)), "applied": applied})
        return out

    can_fold = plan.get("foldable") is True and plan.get("fold") is not False

    def folding(floor: bool) -> list[dict]:
        out: list[dict] = []
        if can_fold and (plan.get("fold") is True or free or plan.get("autoWidth")):
            mw = widths[-1]
            d = plan["start"]
            for share in FOLD_SHARES:
                applied: list[dict] = []
                if mw != from0:
                    applied.append({"what": "maxNodeW", "from": from0, "to": mw, "mode": width_mode})

                def run(share=share, d=d, mw=mw, floor=floor, applied=applied) -> dict:
                    r = plan["build"](d, mw, floor, plan["w"] * share + 0.5)
                    for f in _folded_of(r):
                        applied.append({"what": "fold", "from": f["rows"], "to": f["layer"] + 1, "mode": "auto" if plan.get("autoWidth") else ("written" if plan["explicitDir"] else plan["mode"])})
                    return r

                label = f"dir '{d}', maxNodeW {mw}, fold{f' {js_round(share * 100)}%' if share < 1 else ''}{suffix(floor)}"
                out.append({"label": label, "applied": applied, "run": run})
        return out

    stages = [[*narrowing(False), *folding(False)]] if len(floors) == 1 else [narrowing(True), narrowing(False), folding(True), folding(False)]
    fit_mode = "best" if plan.get("best") else "first"
    height_budget = plan.get("heightBudget")
    width_of = plan.get("widthOf")
    all_tried: list[dict] = []
    all_results: list[dict] = []
    for stage in (s for s in stages if s):
        got = fit_width(plan["w"], stage, fit_mode, height_budget, width_of)
        if got["ok"]:
            return {"ok": True, "result": got["result"], "applied": with_widths(got["applied"], [*all_tried, *got["tried"]], len(all_tried) + got["index"])}
        all_tried.extend(got["tried"])
        all_results.extend(got["results"])

    def failure() -> str:
        fitted = {"tried": all_tried, "results": all_results}
        not_tried: list[str] = []
        if plan["explicitDir"]:
            alt_part = f"dir '{alt}'{' and ' if narrow else ''}" if alt is not None else ""
            narrow_part = "narrower nodes" if narrow else ""
            them_it = "them" if (alt is not None or narrow) else "it"
            not_tried.append(f"{alt_part}{narrow_part} (dir is explicit; write dir: 'auto' to let {them_it} change)")
        elif narrow and not plan.get("autoWidth") and plan.get("maxNodeW") is not None:
            not_tried.append(f"narrower nodes (maxNodeW is explicit: {plan['maxNodeW']})")
        if not plan["explicitDir"] and alt is None and plan.get("axisKept"):
            not_tried.append(plan["axisKept"])
        if plan.get("foldable") and plan.get("fold") is False:
            not_tried.append("folding a layer into rows (fold is written: false)")
        not_tried.extend(plan.get("notTried") or [])
        too_tall = height_budget is not None and any(t.get("fitsWidth", t["w"] <= plan["w"] + 0.5) for t in fitted["tried"])
        wider = wider_than(fitted["tried"], 40)
        if too_tall:
            fix = "split the figure in two (fewer entities or fewer layers), or give the canvas more height"
        elif plan["explicitDir"]:
            fold_hint = "or fold: true (a layer wider than the figure is cut into rows, the direction stays), " if (can_fold and plan.get("fold") is None) else ""
            fix = f"dir: 'auto', {fold_hint}or widen the figure (diagram({{width: {wider}}}))"
        else:
            fix = plan.get("fix") or ("split the figure in two (fewer entities on one level)" if wider > 1400 else f"widen the figure (diagram({{width: {wider}}}))")
        # where to split (ADR 0019 D3): a height failure by the first attempt that fits the width, a width failure by the narrowest one that did not fold
        split: str | None = None
        if plan.get("layoutOf"):
            results = fitted["results"]
            lays = [plan["layoutOf"](r) for r in results]
            if too_tall:
                i = next((idx for idx, t in enumerate(fitted["tried"]) if t.get("fitsWidth", t["w"] <= plan["w"] + 0.5)), -1)
                at_ = lays[i]
                if at_["vertical"] and height_budget is not None:
                    split = split_by_height(at_["lay"], height_budget)
            else:
                unfolded = [(r, i) for i, r in enumerate(results) if "fold" not in fitted["tried"][i]["label"]]
                narrowest = min(unfolded, key=lambda ri: fitted["tried"][ri[1]]["w"], default=None)
                if narrowest is not None:
                    split = split_widest(lays[narrowest[1]]["lay"])
        return fit_failure(plan["who"], plan["w"], fitted["tried"], fix, not_tried, height_budget, split)

    return {"ok": False, "failure": failure}


def fit_layout(plan: dict) -> dict:
    """lib/fit-width.ts:159-163 fitLayout(): plan_fit(), raising (with what was tried and one
    fix) when none fits. Returns {"result": R, "applied": [...]}"""
    got = plan_fit(plan)
    if not got["ok"]:
        raise ValueError(got["failure"]())
    return {"result": got["result"], "applied": got["applied"]}


def is_no_fit(r: dict) -> bool:
    """lib/fit-width.ts's isNoFit()."""
    return "noFit" in r


def fit_or_throw(r: dict) -> dict:
    """lib/fit-width.ts's fitOrThrow(): the layout, or the error fit_layout() would have
    thrown."""
    if is_no_fit(r):
        raise ValueError(r["failure"]())
    return r
