"""1:1 port of lib/quadrant.ts's quadrantBand()/layoutQuadrant() (exported, golden-tested
live) and lib/emit-figures.ts's renderQuadrant() — a classification matrix (2x2, 3x3 or any
N x M cells) with items placed in a cell or at a coordinate, optional bubble sizes, movement
arrows, free-shaped regions and the named presets of management frameworks (BCG, GE-McKinsey,
Ansoff, the nine-box, ...).

quadrantTexts() (Node's text-measurement-batching helper) is not ported — same reasoning as
every other band's *Texts() helper. Spotlight dim/stage filtering (`dim`) and ADR 0034's
`data-node` injection (`withNodeIds`) are not ported either, same scope decision as every
other band in this port — `dataNode` fields are kept in the data shape (defensively rendered
if ever present) but nothing in this port's layout ever sets them.

Golden master: lib/quadrant.ts + lib/emit-figures.ts's renderQuadrant() (Node.js, svg-diagram).
"""

from __future__ import annotations

import math

from .atoms import text_width
from .emit_common import emoji_span, escape_attr, js_num, js_round, round1
from .layout_util import grid_columns
from .tokens import PALETTE, color_of, tone_style
from .wrap import WrapMode, wrap_text

QUADRANT_PRESETS: list[str] = ["bcg", "ge", "ansoff", "nineBox", "impactEffort", "risk", "stakeholder", "positioning", "eisenhower"]


def _c(title: str, note: str | None, tone: str) -> dict:
    out = {"title": title, "tone": tone}
    if note:
        out["note"] = note
    return out


_RISK_RATING = [["低", "低", "中"], ["低", "中", "高"], ["中", "高", "重大"]]  # [likelihood-1][impact-1]
_RISK_TONE: dict[str, str] = {"低": "plain", "中": "changed", "高": "accent", "重大": "danger"}
_RISK_NOTE = ["低", "中", "高"]
_RISK_IMPACT = ["小", "中", "大"]


def _risk_cells() -> list[list[dict]]:
    return [[_c(f"リスク {_RISK_RATING[l][i]}", f"発生 {_RISK_NOTE[l]} × 影響 {_RISK_IMPACT[i]}", _RISK_TONE[_RISK_RATING[l][i]]) for i in range(3)] for l in (2, 1, 0)]


PRESETS: dict[str, dict] = {
    "bcg": {
        "x": {"title": "相対市場シェア", "low": "低", "high": "高", "reversed": True}, "y": {"title": "市場成長率", "low": "低", "high": "高"}, "grid": (2, 2),
        "cells": [[_c("花形", "投資して地位を守る", "accent"), _c("問題児", "選んで育てるか、撤退する", "changed")], [_c("金のなる木", "収穫して他へ回す", "accent"), _c("負け犬", "縮小・撤退を検討する", "muted")]],
    },
    "ge": {
        "x": {"title": "事業の競争力", "low": "弱い", "high": "強い", "reversed": True}, "y": {"title": "業界の魅力度", "low": "低い", "high": "高い"}, "grid": (3, 3),
        "cells": [
            [_c("投資・成長", "魅力 高 × 競争力 強", "accent"), _c("投資・成長", "魅力 高 × 競争力 中", "accent"), _c("選別的投資", "魅力 高 × 競争力 弱", "changed")],
            [_c("投資・成長", "魅力 中 × 競争力 強", "accent"), _c("選別的投資", "魅力 中 × 競争力 中", "changed"), _c("収穫・撤退", "魅力 中 × 競争力 弱", "muted")],
            [_c("選別的投資", "魅力 低 × 競争力 強", "changed"), _c("収穫・撤退", "魅力 低 × 競争力 中", "muted"), _c("収穫・撤退", "魅力 低 × 競争力 弱", "muted")],
        ],
    },
    "ansoff": {
        "x": {"title": "製品", "low": "既存", "high": "新規"}, "y": {"title": "市場", "low": "既存", "high": "新規", "reversed": True}, "grid": (2, 2),
        "cells": [[_c("市場浸透", "既存の市場に既存の製品で攻める", "accent"), _c("新製品開発", "既存の市場に新製品を出す", "changed")], [_c("新市場開拓", "既存の製品を新しい市場へ", "changed"), _c("多角化", "新製品を新しい市場へ（最も高リスク）", "danger")]],
    },
    "nineBox": {
        "x": {"title": "業績", "low": "低い", "high": "高い"}, "y": {"title": "潜在能力", "low": "低い", "high": "高い"}, "grid": (3, 3),
        "cells": [
            [_c("原石", "業績 低 × 潜在 高", "muted"), _c("有望株", "業績 中 × 潜在 高", "changed"), _c("スター", "業績 高 × 潜在 高", "accent")],
            [_c("要改善", "業績 低 × 潜在 中", "muted"), _c("堅実人材", "業績 中 × 潜在 中", "plain"), _c("中核人材", "業績 高 × 潜在 中", "changed")],
            [_c("要対応", "業績 低 × 潜在 低", "removed"), _c("貢献人材", "業績 中 × 潜在 低", "plain"), _c("専門人材", "業績 高 × 潜在 低", "plain")],
        ],
    },
    "impactEffort": {
        "x": {"title": "実行容易性", "low": "難しい", "high": "易しい"}, "y": {"title": "インパクト", "low": "小さい", "high": "大きい"}, "grid": (2, 2),
        "cells": [[_c("大型案件", "効果は大きいが難しい。計画して挑む", "changed"), _c("クイックウィン", "効果が大きく易しい。まずやる", "accent")], [_c("後回し", "効果が小さく難しい。手を付けない", "muted"), _c("ついでに", "効果は小さいが易しい。余力で", "changed")]],
    },
    "risk": {"x": {"title": "影響度", "low": "小", "high": "大"}, "y": {"title": "発生可能性", "low": "低", "high": "高"}, "grid": (3, 3), "cells": _risk_cells()},
    "stakeholder": {
        "x": {"title": "関心度", "low": "低い", "high": "高い"}, "y": {"title": "影響力", "low": "小さい", "high": "大きい"}, "grid": (2, 2),
        "cells": [[_c("満足させる", "影響力は大。要望を先に聞く", "changed"), _c("重点管理", "影響力も関心も大。密に連携する", "accent")], [_c("監視", "最小限の労力で見守る", "muted"), _c("情報提供", "関心は大。こまめに知らせる", "changed")]],
    },
    "positioning": {
        "x": {"title": "価格", "low": "安い", "high": "高い"}, "y": {"title": "機能の充実度", "low": "少ない", "high": "多い"}, "grid": (2, 2),
        "cells": [[_c("", None, "plain"), _c("", None, "plain")], [_c("", None, "plain"), _c("", None, "plain")]], "crosshair": True, "height": 400,
    },
    "eisenhower": {
        "x": {"title": "緊急度", "low": "低い", "high": "高い", "reversed": True}, "y": {"title": "重要度", "low": "低い", "high": "高い"}, "grid": (2, 2),
        "cells": [[_c("今すぐやる", "重要で緊急。自分で片付ける", "accent"), _c("計画してやる", "重要だが急がない。日程に入れる", "accent")], [_c("任せる", "緊急だが重要でない。人に頼む", "plain"), _c("やめる", "重要でも緊急でもない。減らす", "muted")]],
    },
}

# ---------------------------------------------------------------------------------------------------------------------------
# validation and normalising
# ---------------------------------------------------------------------------------------------------------------------------

_MAX_GRID = 8
SHAPES: list[str] = ["circle", "square", "diamond", "triangle"]
_GROUP_TONES: list[str] = ["accent", "text", "danger", "muted"]
_ITEM_TONES: list[str] = ["accent", "text", "muted", "danger"]
_CELL_TONES: list[str] = ["plain", "accent", "new", "changed", "removed", "muted", "danger"]
_HOLD: dict[str, float] = {"circle": 1, "square": 1.26, "diamond": 1.26, "triangle": 1.56}


def _group_style(gi: int) -> dict:
    """The marker of the n-th group: a shape and a colour, and from the fifth group on a
    hollow shape, so that no two groups differ by colour alone (up to 8)."""
    return {"shape": SHAPES[gi % len(SHAPES)], "tone": _GROUP_TONES[(gi + gi // len(SHAPES)) % len(_GROUP_TONES)], "hollow": gi >= len(SHAPES)}


def _defined(d: dict | None) -> dict:
    return {k: v for k, v in (d or {}).items() if v is not None}


def quadrant_band(opts: dict) -> dict:
    """lib/quadrant.ts:243-340 quadrantBand(). Validates the options, applies the preset and
    returns the band. Every error names the item / option."""
    if not isinstance(opts, dict):
        raise ValueError("quadrant({...}) takes an options object")
    preset = opts.get("preset")
    if preset is not None and preset not in QUADRANT_PRESETS:
        raise ValueError(f"quadrant(): unknown preset \"{preset}\" ({' / '.join(QUADRANT_PRESETS)})")
    p = PRESETS[preset] if preset else None
    if opts.get("grid") is not None:
        shape = tuple(opts["grid"])
    elif p is not None:
        shape = p["grid"]
    elif opts.get("cells") is not None:
        shape = (max(2, max((len(r) for r in opts["cells"]), default=0)), max(1, len(opts["cells"])))
    else:
        shape = (2, 2)
    cols, rows = shape
    if not isinstance(cols, int) or isinstance(cols, bool) or not isinstance(rows, int) or isinstance(rows, bool) or cols < 1 or rows < 1 or cols > _MAX_GRID or rows > _MAX_GRID:
        raise ValueError(f"quadrant(): grid must be whole numbers [cols, rows] from 1 to {_MAX_GRID} (got [{cols}, {rows}])")
    if cols * rows < 2:
        raise ValueError("quadrant(): a grid of one cell is not a matrix")

    def axis(k: str) -> dict:
        # JS's `{...p?.[k], ...}` spreads nothing when p is missing or lacks k (object spread
        # of undefined is a no-op); Python's ** needs an actual mapping, so both cases fall
        # back to {} explicitly (p truthy but missing k was the one case the previous
        # `p.get(k) if p else {}` didn't cover).
        a = {**((p or {}).get(k) or {}), **_defined(opts.get(k))}
        if not a.get("title"):
            raise ValueError(f"quadrant(): axis {k} needs a title ({k}: {{title: '市場成長率', low: '低', high: '高'}})")
        return a

    x, y = axis("x"), axis("y")
    # the preset's captions only fit the preset's own grid
    base = p["cells"] if p and tuple(p["grid"]) == (cols, rows) else None
    if opts.get("cells") is not None:
        if len(opts["cells"]) > rows:
            raise ValueError(f"quadrant(): cells has {len(opts['cells'])} rows but the grid has {rows}")
        for i, r in enumerate(opts["cells"]):
            if len(r) > cols:
                raise ValueError(f"quadrant(): cells row {i + 1} has {len(r)} cells but the grid has {cols} columns")
    cells: list[list[dict]] = []
    for r in range(rows):
        row = []
        for k in range(cols):
            base_cell = base[r][k] if base and r < len(base) and k < len(base[r]) else {}
            opt_cell = opts.get("cells", [])
            opt_cell = opt_cell[r][k] if r < len(opt_cell) and k < len(opt_cell[r]) else None
            merged = {**base_cell, **_defined(opt_cell)}
            for key in ("title", "note"):
                if merged.get(key) == "":
                    del merged[key]
            row.append(merged)
        cells.append(row)
    for r, row in enumerate(cells):
        for k, cell in enumerate(row):
            if cell.get("tone") is not None and cell["tone"] not in _CELL_TONES:
                raise ValueError(f"quadrant(): cell [{k}, {r}] has tone \"{cell['tone']}\" ({' / '.join(_CELL_TONES)})")
    items = [dict(it) for it in (opts.get("items") or [])]
    ids: set[str] = set()
    for i, it in enumerate(items):
        what = f"quadrant() item {i + 1}" + (f' "{it["label"]}"' if it.get("label") else "")
        if not it or not isinstance(it.get("label"), str) or not it["label"]:
            raise ValueError(f"{what}: needs a label")
        if (it.get("cell") is None) == (it.get("at") is None):
            raise ValueError(f"{what}: give exactly one of cell: [col, row] or at: [x, y]")
        if it.get("cell") is not None:
            cc, rr = it["cell"]
            if not isinstance(cc, int) or isinstance(cc, bool) or not isinstance(rr, int) or isinstance(rr, bool) or cc < 0 or rr < 0 or cc >= cols or rr >= rows:
                raise ValueError(f"{what}: cell [{cc}, {rr}] is outside the {cols} x {rows} grid (columns 0..{cols - 1}, rows 0..{rows - 1}, from the top-left)")
        if it.get("at") is not None:
            at = it["at"]
            ok = isinstance(at, (list, tuple)) and len(at) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 for v in at)
            if not ok:
                raise ValueError(f"{what}: at must be [x, y] with both from 0 to 1 (got {list(at) if isinstance(at, (list, tuple)) else at}); 1 is the high end of the axis")
        if it.get("size") is not None and not (isinstance(it["size"], (int, float)) and not isinstance(it["size"], bool) and it["size"] > 0 and math.isfinite(it["size"])):
            raise ValueError(f"{what}: size must be a number > 0 (got {it.get('size')})")
        if it.get("tone") is not None and it["tone"] not in _ITEM_TONES:
            raise ValueError(f"{what}: tone must be {' / '.join(_ITEM_TONES)} (got {it.get('tone')!r})")
        if it.get("group") is not None and (not isinstance(it["group"], str) or not it["group"]):
            raise ValueError(f"{what}: group must be a non-empty string (got {it.get('group')!r})")
        if it.get("id") is not None:
            if it["id"] in ids:
                raise ValueError(f"{what}: the id \"{it['id']}\" is used twice")
            ids.add(it["id"])
    arrows = [dict(a) for a in (opts.get("arrows") or [])]
    for i, a in enumerate(arrows):
        for k in ("from", "to"):
            e = a[k]
            if isinstance(e, str):
                if e not in ids:
                    raise ValueError(f"quadrant() arrow {i + 1}: {k} \"{e}\" is not the id of an item (items: {', '.join(ids) or 'none have an id'})")
            elif not (isinstance(e, (list, tuple)) and len(e) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1 for v in e)):
                raise ValueError(f"quadrant() arrow {i + 1}: {k} must be an item id or [x, y] from 0 to 1")
    sizes = [i for i in items if i.get("size") is not None]
    if (opts.get("sizeTitle") is not None or opts.get("sizeUnit") is not None) and not sizes:
        raise ValueError("quadrant(): sizeTitle / sizeUnit describe the bubble sizes, but no item has a size")
    # a bubble without a size would read as a small value: either every item has a size or none has
    unsized = next((i for i, it in enumerate(items) if it.get("size") is None), -1)
    if sizes and unsized >= 0:
        raise ValueError(f"quadrant() item {unsized + 1} \"{items[unsized]['label']}\": has no size, but other items do — give every item a size (its bubble would read as a small value), or none")
    groups = list(opts.get("groups") or [])
    if len(set(groups)) != len(groups):
        raise ValueError(f"quadrant(): groups lists a name twice ({', '.join(groups)})")
    # an item without a group would look like the first group's marker
    ungrouped = next((i for i, it in enumerate(items) if it.get("group") is None), -1)
    if any(it.get("group") is not None for it in items) and ungrouped >= 0:
        raise ValueError(f"quadrant() item {ungrouped + 1} \"{items[ungrouped]['label']}\": has no group, but other items do — give every item a group (it would look like the first group's marker), or none")
    for it in items:
        if it.get("group") is not None and it["group"] not in groups:
            groups.append(it["group"])
    if len(groups) > len(SHAPES) * 2:
        raise ValueError(f"quadrant(): {len(groups)} groups — at most {len(SHAPES) * 2} can be told apart by shape and colour")
    allow_empty = opts.get("allowEmpty")
    if allow_empty is not None and allow_empty is not True and not isinstance(allow_empty, list):
        raise ValueError(f"quadrant(): allowEmpty must be true or a list of [col, row] cells (got {allow_empty!r})")
    if allow_empty is not None and allow_empty is not True:
        for e in allow_empty:
            if not isinstance(e, (list, tuple)) or len(e) != 2 or not isinstance(e[0], int) or isinstance(e[0], bool) or not isinstance(e[1], int) or isinstance(e[1], bool) or e[0] < 0 or e[1] < 0 or e[0] >= cols or e[1] >= rows:
                raise ValueError(f"quadrant(): allowEmpty cell {list(e)} is outside the {cols} x {rows} grid (columns 0..{cols - 1}, rows 0..{rows - 1}, from the top-left), or use true")
    for k in ("height", "width"):
        v = opts.get(k)
        if v is not None and not (isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 and math.isfinite(v)):
            raise ValueError(f"quadrant(): {k} must be a finite number > 0 (got {v})")
    regions = [{**r, "points": [list(pt) for pt in r["points"]]} for r in (opts.get("regions") or [])]
    crosshair = opts.get("crosshair") if opts.get("crosshair") is not None else (p.get("crosshair") if p else False) or False
    if regions:
        if not crosshair:
            raise ValueError("quadrant(): regions are drawn over one continuous plot — write crosshair: true (or the preset \"positioning\")")
        if any(cell.get("title") or cell.get("note") for row in cells for cell in row):
            raise ValueError("quadrant(): regions carry the words of the figure, so the cells must have no title / note (a caption strip would shift the items off the regions) — use preset \"positioning\" or leave cells out")

    def unit(v: object) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1

    for i, r in enumerate(regions):
        what = f"quadrant() region {i + 1}" + (f' "{r["title"]}"' if r.get("title") else "")
        if not r or not isinstance(r.get("title"), str) or not r["title"]:
            raise ValueError(f"{what}: needs a title (the region's name in words)")
        if not isinstance(r.get("points"), list) or len(r["points"]) < 3 or not all(isinstance(pt, (list, tuple)) and len(pt) == 2 and all(unit(v) for v in pt) for pt in r["points"]):
            raise ValueError(f"{what}: points must be at least 3 corners [x, y], each from 0 to 1 (got {r.get('points')})")
        if r.get("at") is not None and not (isinstance(r["at"], (list, tuple)) and len(r["at"]) == 2 and all(unit(v) for v in r["at"])):
            raise ValueError(f"{what}: at must be [x, y] with both from 0 to 1 (got {r.get('at')})")
        if r.get("tone") is not None and r["tone"] not in _CELL_TONES:
            raise ValueError(f"{what}: tone must be {' / '.join(_CELL_TONES)} (got {r.get('tone')!r})")
    band: dict = {"type": "quadrant"}
    if opts.get("id") is not None:
        band["id"] = opts["id"]
    if opts.get("reveal") is not None:
        band["reveal"] = opts["reveal"]
    if opts.get("until") is not None:
        band["until"] = opts["until"]
    band.update({"x": x, "y": y, "cols": cols, "rows": rows, "cells": cells, "items": items, "arrows": arrows, "groups": groups, "crosshair": crosshair, "regions": regions})
    if opts.get("sizeTitle") is not None:
        band["sizeTitle"] = opts["sizeTitle"]
    if opts.get("sizeUnit") is not None:
        band["sizeUnit"] = opts["sizeUnit"]
    height = opts.get("height") if opts.get("height") is not None else (p.get("height") if p else None)
    if height is not None:
        band["height"] = height
    if opts.get("width") is not None:
        band["width"] = opts["width"]
    if allow_empty is not None:
        band["allowEmpty"] = True if allow_empty is True else [[c, r] for c, r in allow_empty]
    return band


def quadrant_ids(b: dict) -> list[str]:
    """lib/quadrant.ts:343 quadrantIds() — the anchor ids of the band's items (read before
    layout, so reveal gives each the figure's stage)."""
    return [i["id"] for i in b["items"] if i.get("id")]

# ---------------------------------------------------------------------------------------------------------------------------
# sizes
# ---------------------------------------------------------------------------------------------------------------------------


def _fmt_num(n: float) -> str:
    """JS `n.toLocaleString('en-US', {maximumFractionDigits: 6})`."""
    s = f"{n:,.6f}".rstrip("0").rstrip(".")
    return s if s else "0"


def size_refs(max_v: float) -> list[float]:
    """lib/quadrant.ts:351-355 sizeRefs(): reference values for the size legend: the largest
    1 / 2 / 5 x 10^k not above the biggest size, and a tenth of it."""
    mag = 10 ** math.floor(math.log10(max_v))
    v = next((m * mag for m in (5, 2, 1) if m * mag <= max_v * (1 + 1e-9)), mag)
    return [v, v / 10]


def _size_legend_title(b: dict) -> str:
    return f"円の面積 = {b.get('sizeTitle') or '大きさ'}"


def _size_ref_label(b: dict, v: float) -> str:
    return f"{_fmt_num(v)}{b.get('sizeUnit') or ''}"


def _max_size(b: dict) -> float:
    return max([0.0] + [i.get("size") or 0 for i in b["items"]])

# ---------------------------------------------------------------------------------------------------------------------------
# layout
# ---------------------------------------------------------------------------------------------------------------------------

_SIDES = ["right", "left", "below", "above", "below-right", "below-left", "above-right", "above-left"]
_FLOW_SIDES = ["below", "right", "left", "above", "below-right", "below-left", "above-right", "above-left"]
_GAP, _PAD, _MARGIN = 4, 8, 3
_MIN_R = 6


def _g4(v: float) -> float:
    return js_round(v / 4) * 4


def _build_offsets() -> list[tuple[int, int, float]]:
    seen: set[str] = set()
    out: list[tuple[int, int, float]] = []

    def add(dx: int, dy: int) -> None:
        k = f"{dx},{dy}"
        if k not in seen:
            seen.add(k)
            out.append((dx, dy, math.hypot(dx, dy)))

    for dy in range(-60, 61, 4):
        for dx in range(-60, 61, 4):
            add(dx, dy)
    for dy in range(-480, 481, 8):
        for dx in range(-480, 481, 8):
            add(dx, dy)
    out.sort(key=lambda t: (t[2], t[1], t[0]))
    return out


_OFFSETS = _build_offsets()
_MAX_MOVE = 56


def _circle_rect(cx: float, cy: float, r: float, b: dict, m: float = 0) -> bool:
    nx, ny = max(b["x"], min(cx, b["x"] + b["w"])), max(b["y"], min(cy, b["y"] + b["h"]))
    return math.hypot(cx - nx, cy - ny) < r + m


def _rects_meet(a: dict, b: dict, m: float = 0) -> bool:
    return a["x"] < b["x"] + b["w"] + m and b["x"] < a["x"] + a["w"] + m and a["y"] < b["y"] + b["h"] + m and b["y"] < a["y"] + a["h"] + m


def _inside(a: dict, b: dict) -> bool:
    return a["x"] >= b["x"] and a["y"] >= b["y"] and a["x"] + a["w"] <= b["x"] + b["w"] and a["y"] + a["h"] <= b["y"] + b["h"]


def _segment_meets(s: dict, r: dict, m: float = 1) -> bool:
    """Does the segment pass within `m` of the rect (sampled every 3px)?"""
    n = max(1, math.ceil(math.hypot(s["x2"] - s["x1"], s["y2"] - s["y1"]) / 3))
    for i in range(n + 1):
        px, py = s["x1"] + (s["x2"] - s["x1"]) * i / n, s["y1"] + (s["y2"] - s["y1"]) * i / n
        if r["x"] - m <= px <= r["x"] + r["w"] + m and r["y"] - m <= py <= r["y"] + r["h"] + m:
            return True
    return False


class _Grow(Exception):
    def __init__(self, why: str) -> None:
        super().__init__(why)
        self.why = why


def layout_quadrant(band: dict, x: float, y: float, w: float, width_of, roles: dict, mode: WrapMode) -> dict:
    """lib/quadrant.ts:424-758 layoutQuadrant()."""
    size, t_size = roles["note"], roles["title"]
    line_n, line_t = size + 4, t_size + 5

    def tw(s: str, sz: float, weight: float = 400) -> float:
        return text_width(width_of, s, sz, weight)

    def wrap(s: str, sz: float, weight: float, max_w: float) -> list[str]:
        return wrap_text(s, max_width=max(20, max_w), atom_width=lambda a: width_of(a, sz, weight, "sans"), mode=mode)

    def widest(lines: list[str], sz: float, weight: float) -> float:
        return max([0.0] + [tw(l, sz, weight) for l in lines])

    width = min(w, band.get("width") or w)
    left = x + (w - width) / 2
    cols, rows = band["cols"], band["rows"]

    # ---- axes: the y names sit in a gutter left of the plot, the x names in a row under it
    gutter_max = max(80, min(150, width * 0.2))
    y_title = wrap(band["y"]["title"], t_size, 700, gutter_max)
    gutter_w = math.ceil(max(widest(y_title, t_size, 700), tw(band["y"].get("high") or "", size), tw(band["y"].get("low") or "", size))) + 14
    # the plot's edges are on the 4px grid the emitter snaps to, and so are the cells (ADR 0014 D1): equal columns, even gutters
    plot_l = math.ceil((left + _PAD + gutter_w) / 4 - 1e-9) * 4
    plot_r = math.floor((left + width - _PAD) / 4 + 1e-9) * 4
    plot_w = plot_r - plot_l
    x_left = (band["x"].get("high") if band["x"].get("reversed") else band["x"].get("low")) or ""
    x_right = (band["x"].get("low") if band["x"].get("reversed") else band["x"].get("high")) or ""
    if tw(x_left, size) + tw(band["x"]["title"], t_size, 700) + tw(x_right, size) + 36 > plot_w:
        raise ValueError(f"quadrant(): the x axis names do not fit under the plot ({round(plot_w)}px): shorten the title / low / high, or widen the figure")
    gap = 0 if band["crosshair"] else 6  # between rows (unchanged)
    hgap = 0 if band["crosshair"] else 8  # between columns: a multiple of 4
    col_grid = grid_columns(plot_w, cols, hgap, fixed_gap=band["crosshair"], any_gap=True)
    if col_grid is None:
        col_w = (plot_w - hgap * (cols - 1)) / cols
        col_grid = {"x": [k * (col_w + hgap) for k in range(cols)], "w": [col_w] * cols}
    cw = min(col_grid["w"])  # the narrowest cell: what the wrapping is measured against
    if cw < 90:
        raise ValueError(f"quadrant(): {cols} columns leave {round(cw)}px per cell — fewer columns or a wider figure")

    # ---- captions: a header strip per row
    cap_w = cw - 20
    caps = [[{"t": wrap(cell["title"], t_size, 700, cap_w) if cell.get("title") else [], "n": wrap(cell["note"], size, 400, cap_w) if cell.get("note") else []} for cell in row] for row in band["cells"]]
    hdr = [max([0.0] + [8 + len(k["t"]) * line_t + len(k["n"]) * line_n + 6 if len(k["t"]) + len(k["n"]) else 0 for k in row]) for row in caps]

    # ---- the items: radius, label lines
    mx = _max_size(band)

    def group_index(g: str | None) -> int:
        return -1 if g is None else band["groups"].index(g)

    base_row = max(band.get("height") or (340 if rows == 2 else 120 * rows + 90), 0) / rows
    r_max = max(14, min(44, min(cw, base_row - max(hdr)) * 0.2))
    label_w = max(70, min(150, cw * 0.55))
    units: list[dict] = []
    for i, item in enumerate(band["items"]):
        gi = group_index(item.get("group"))
        shape = "circle" if gi < 0 else _group_style(gi)["shape"]
        hollow = gi >= 0 and _group_style(gi)["hollow"]
        tone = item.get("tone") or ("accent" if gi < 0 else _group_style(gi)["tone"])
        r = 8 if item.get("size") is None or mx <= 0 else max(_MIN_R, r_max * math.sqrt(item["size"] / mx))
        wrapped = wrap(item["label"], size, 400, label_w)
        units.append({"i": i, "item": item, "r": r, "cr": r * _HOLD[shape], "shape": shape, "tone": tone, "hollow": hollow, "lines": wrapped, "lw": widest(wrapped, size, 400), "lh": len(wrapped) * line_n, "col": 0, "row": 0})
    floored = [u["item"]["label"] for u in units if mx > 0 and u["item"].get("size") is not None and r_max * math.sqrt(u["item"]["size"] / mx) < _MIN_R - 0.5]

    # ---- cell-placed items: a row-wrapped flow per cell (each unit a bubble with its label below)
    flow_w = cw - 16

    def uw(u: dict) -> float:
        return max(2 * u["cr"], u["lw"])

    def uh(u: dict) -> float:
        return 2 * u["cr"] + _GAP + u["lh"]

    flows: dict[tuple[int, int], dict] = {}
    for k in range(cols):
        for r in range(rows):
            mine = [u for u in units if u["item"].get("cell") is not None and u["item"]["cell"][0] == k and u["item"]["cell"][1] == r]
            if not mine:
                continue
            for u in mine:
                if uw(u) > flow_w:
                    raise ValueError(f"quadrant(): the label \"{u['item']['label']}\" is wider than its cell ({round(flow_w)}px) — shorten it or widen the figure")
            flow_rows: list[list[dict]] = [[]]
            used = 0.0
            for u in mine:
                cur = flow_rows[-1]
                if cur and used + 12 + uw(u) > flow_w:
                    flow_rows.append([u])
                    used = uw(u)
                else:
                    used += (12 if cur else 0) + uw(u)
                    cur.append(u)
            heights = [max(uh(u) for u in fr) for fr in flow_rows]
            flows[(k, r)] = {"rows": flow_rows, "heights": heights, "total": sum(heights) + 10 * (len(flow_rows) - 1)}
    flow_need = [max([0.0] + [f["total"] + 12 for (k, r), f in flows.items() if r == rr]) for rr in range(rows)]

    # ---- one attempt at a layout with the rows grown by `grow`
    def attempt(grow: float, move_limit: float) -> dict:
        plot_h0 = max(band.get("height") or (340 if rows == 2 else 120 * rows + 90), rows * (max(hdr) + 90))
        row_h = [max(plot_h0 / rows * grow, hdr[r] + 90, hdr[r] + flow_need[r]) for r in range(rows)]
        plot_t = y + _PAD
        plot_h = sum(row_h) + gap * (rows - 1)
        plot_b = plot_t + plot_h
        row_top = [plot_t + sum(row_h[:r]) + gap * r for r in range(rows)]

        def col_w(k: int) -> float:
            return col_grid["w"][k]

        def cell_x(k: int) -> float:
            return plot_l + col_grid["x"][k]

        def cell_rect(k: int, r: int) -> dict:
            return {"x": cell_x(k), "y": row_top[r], "w": col_w(k), "h": row_h[r]}

        def body_rect(k: int, r: int) -> dict:
            return {"x": cell_x(k), "y": row_top[r] + hdr[r], "w": col_w(k), "h": row_h[r] - hdr[r]}

        plot = {"x": plot_l, "y": plot_t, "w": plot_w, "h": plot_h}

        # value space -> pixels (a value is mapped into the body of the cell it falls in)
        def to_cell(vx: float, vy: float) -> dict:
            ix, iy = min(cols - 1, math.floor(vx * cols)), min(rows - 1, math.floor(vy * rows))
            fx, fy = vx * cols - ix, vy * rows - iy
            col = cols - 1 - ix if band["x"].get("reversed") else ix
            row = iy if band["y"].get("reversed") else rows - 1 - iy
            bd = body_rect(col, row)
            return {"col": col, "row": row, "x": bd["x"] + (1 - fx if band["x"].get("reversed") else fx) * bd["w"], "y": bd["y"] + (fy if band["y"].get("reversed") else 1 - fy) * bd["h"]}

        texts: list[dict] = []
        label_boxes: list[dict] = []
        headers: list[dict] = []

        # ---- captions
        for r, row_cells in enumerate(band["cells"]):
            for k, cell in enumerate(row_cells):
                cap, cr0 = caps[r][k], cell_rect(k, r)
                ink = "accent" if cell.get("tone") == "accent" else "danger" if cell.get("tone") == "danger" else "text"
                top = cr0["y"] + 8
                for line in cap["t"]:
                    texts.append({"text": line, "x": cr0["x"] + 10, "y": top + t_size, "anchor": "start", "size": t_size, "bold": True, "fill": ink})
                    top += line_t
                for line in cap["n"]:
                    texts.append({"text": line, "x": cr0["x"] + 10, "y": top + size, "anchor": "start", "size": size, "bold": False, "fill": "muted"})
                    top += line_n
                if len(cap["t"]) + len(cap["n"]):
                    wd = max(widest(cap["t"], t_size, 700), widest(cap["n"], size, 400))
                    box = {"x": cr0["x"] + 10, "y": cr0["y"] + 8, "w": wd, "h": top - cr0["y"] - 8}
                    headers.append(box)
                    label_boxes.append({**box, "label": " ".join([*cap["t"], *cap["n"]]), "kind": "caption"})

        # ---- free-shaped regions: pixel polygons over the plot and their captions
        def plot_px(vx: float, vy: float) -> list[float]:
            return [plot_l + (1 - vx if band["x"].get("reversed") else vx) * plot_w, plot_t + vy * plot_h if band["y"].get("reversed") else plot_b - vy * plot_h]

        region_polys = [{"points": [plot_px(vx, vy) for vx, vy in r["points"]], "tone": r.get("tone") or "plain"} for r in band["regions"]]
        region_w = max(90, min(plot_w * 0.3, 190))
        for r in band["regions"]:
            t = wrap(r["title"], t_size, 700, region_w)
            n = wrap(r["note"], size, 400, region_w) if r.get("note") else []
            at = r.get("at") or [sum(pt[0] for pt in r["points"]) / len(r["points"]), sum(pt[1] for pt in r["points"]) / len(r["points"])]
            cx0, cy0 = plot_px(at[0], at[1])
            wd = max(widest(t, t_size, 700), widest(n, size, 400))
            hh = len(t) * line_t + len(n) * line_n
            # the caption stays inside the plot
            cx = min(plot_r - _MARGIN - wd / 2, max(plot_l + _MARGIN + wd / 2, cx0))
            top = min(plot_b - _MARGIN - hh, max(plot_t + _MARGIN, cy0 - hh / 2))
            ty = top
            ink = "accent" if r.get("tone") == "accent" else "danger" if r.get("tone") == "danger" else "text"
            for line in t:
                texts.append({"text": line, "x": cx, "y": ty + t_size, "anchor": "middle", "size": t_size, "bold": True, "fill": ink})
                ty += line_t
            for line in n:
                texts.append({"text": line, "x": cx, "y": ty + size, "anchor": "middle", "size": size, "bold": False, "fill": "muted"})
                ty += line_n
            box = {"x": cx - wd / 2, "y": top, "w": wd, "h": hh}
            headers.append(box)
            label_boxes.append({**box, "label": " ".join([*t, *n]), "kind": "caption"})

        # ---- placing items: the bubble and its label are one unit, checked against everything placed before
        placed: list[dict] = []

        def label_at(u: dict, side: str, cx: float, cy: float) -> dict:
            d = u["cr"] * 0.71 + 2
            if side == "right":
                return {"x": cx + u["cr"] + _GAP, "y": cy - u["lh"] / 2, "w": u["lw"], "h": u["lh"], "anchor": "start", "tx": cx + u["cr"] + _GAP}
            if side == "left":
                return {"x": cx - u["cr"] - _GAP - u["lw"], "y": cy - u["lh"] / 2, "w": u["lw"], "h": u["lh"], "anchor": "end", "tx": cx - u["cr"] - _GAP}
            if side == "below":
                return {"x": cx - u["lw"] / 2, "y": cy + u["cr"] + _GAP, "w": u["lw"], "h": u["lh"], "anchor": "middle", "tx": cx}
            if side == "above":
                return {"x": cx - u["lw"] / 2, "y": cy - u["cr"] - _GAP - u["lh"], "w": u["lw"], "h": u["lh"], "anchor": "middle", "tx": cx}
            if side == "below-right":
                return {"x": cx + d, "y": cy + d, "w": u["lw"], "h": u["lh"], "anchor": "start", "tx": cx + d}
            if side == "below-left":
                return {"x": cx - d - u["lw"], "y": cy + d, "w": u["lw"], "h": u["lh"], "anchor": "end", "tx": cx - d}
            if side == "above-right":
                return {"x": cx + d, "y": cy - d - u["lh"], "w": u["lw"], "h": u["lh"], "anchor": "start", "tx": cx + d}
            return {"x": cx - d - u["lw"], "y": cy - d - u["lh"], "w": u["lw"], "h": u["lh"], "anchor": "end", "tx": cx - d}

        in_plot = {"x": plot_l + _MARGIN, "y": plot_t + _MARGIN, "w": plot_w - 2 * _MARGIN, "h": plot_h - 2 * _MARGIN}

        # the bubble and its label stay inside the item's own cell
        def free(u: dict, cx: float, cy: float, box: dict, extra: list[dict] | None = None) -> bool:
            c0 = cell_rect(u["col"], u["row"])
            cell = {"x": c0["x"] + _MARGIN, "y": c0["y"] + _MARGIN, "w": c0["w"] - 2 * _MARGIN, "h": c0["h"] - 2 * _MARGIN}
            if cx - u["cr"] < cell["x"] or cx + u["cr"] > cell["x"] + cell["w"] or cy - u["cr"] < cell["y"] or cy + u["cr"] > cell["y"] + cell["h"] or not _inside(box, cell):
                return False
            if any(_rects_meet(box, hd, 2) or _circle_rect(cx, cy, u["cr"], hd, 2) for hd in headers):
                return False
            for p in placed:
                o = p["u"]
                if math.hypot(cx - p["spot"]["cx"], cy - p["spot"]["cy"]) < u["cr"] + o["cr"] + 4:
                    return False
                if _circle_rect(cx, cy, u["cr"], p["spot"]["box"], 2) or _circle_rect(p["spot"]["cx"], p["spot"]["cy"], o["cr"], box, 2) or _rects_meet(box, p["spot"]["box"], 2):
                    return False
            return not any(_segment_meets(e["s"], box) for e in (extra or []))

        def try_at(u: dict, cx: float, cy: float, sides: list[str]) -> dict | None:
            for side in sides:
                box = label_at(u, side, cx, cy)
                if free(u, cx, cy, box):
                    return {"cx": cx, "cy": cy, "side": side, "box": box}
            return None

        moved: list[dict] = []

        def settle(u: dict, ax: float, ay: float, sides: list[str], home: dict, limit: float) -> dict | None:
            for dx, dy, dist in _OFFSETS:
                if dist > limit:
                    break
                cx, cy = ax + dx, ay + dy
                if cx < home["x"] or cx > home["x"] + home["w"] or cy < home["y"] or cy > home["y"] + home["h"]:
                    continue  # the centre stays in the body of its own cell
                s = try_at(u, cx, cy, sides)
                if s:
                    return s
            return None

        for u in units:
            if u["item"].get("at") is not None:
                t = to_cell(u["item"]["at"][0], u["item"]["at"][1])
                u["col"], u["row"], u["ideal"] = t["col"], t["row"], {"x": t["x"], "y": t["y"]}
            else:
                u["col"], u["row"] = u["item"]["cell"]
                u["ideal"] = None
        # coordinates first: they are where the author put them; the cell-placed items route around them
        for u in units:
            if not u["ideal"]:
                continue
            ideal = u["ideal"]
            s = settle(u, _g4(ideal["x"]), _g4(ideal["y"]), _SIDES, body_rect(u["col"], u["row"]), move_limit)
            if not s:
                raise _Grow(f"\"{u['item']['label']}\" has no free spot {f'within {move_limit}px of its coordinates' if move_limit < 1e6 else 'in its cell'}")
            placed.append({"u": u, "spot": s})
            px = math.hypot(s["cx"] - ideal["x"], s["cy"] - ideal["y"])
            if px > 3:
                moved.append({"id": u["item"].get("id"), "label": u["item"]["label"], "px": px})
        for (k, r), flow in flows.items():
            body = body_rect(k, r)
            flow_rows, row_hs, total = flow["rows"], flow["heights"], flow["total"]
            n = sum(len(fr) for fr in flow_rows)
            if total > body["h"] - 10:
                raise _Grow(f"the cell [{k}, {r}] cannot hold {n} item{'s' if n > 1 else ''}")
            top = body["y"] + (body["h"] - total) / 2
            for fi, fr in enumerate(flow_rows):
                rw = sum(uw(u) for u in fr) + 12 * (len(fr) - 1)
                cx0 = body["x"] + (body["w"] - rw) / 2
                for u in fr:
                    cx, cy = _g4(cx0 + uw(u) / 2), _g4(top + u["cr"])
                    cx0 += uw(u) + 12
                    s = try_at(u, cx, cy, ["below"]) or settle(u, _g4(body["x"] + body["w"] / 2), _g4(body["y"] + body["h"] / 2), _FLOW_SIDES, body, 1e9)
                    if not s:
                        raise _Grow(f"\"{u['item']['label']}\" has no free spot in its cell")
                    placed.append({"u": u, "spot": s})
                top += row_hs[fi] + 10

        return {"regionPolys": region_polys, "rowH": row_h, "plotT": plot_t, "plotB": plot_b, "plot": plot, "placed": placed, "moved": moved, "texts": texts, "labelBoxes": label_boxes, "headers": headers, "cellRect": cell_rect, "toCell": to_cell, "inPlot": in_plot, "free": free, "labelAt": label_at}

    result = None
    last_why = ""
    # first keep every item near its coordinates and grow the rows; as a last resort let a crowded item move anywhere in its cell
    for limit, tries in ((_MAX_MOVE, 9), (1e9, 4)):
        for k in range(tries):
            if result is not None:
                break
            try:
                result = attempt(1 + k * 0.25, limit)
            except _Grow as e:
                last_why = e.why
    if result is None:
        raise ValueError(f"quadrant(): {last_why}, even with the rows grown — fewer items, smaller sizes, a wider figure or a coarser grid")
    region_polys, row_h, plot_t, plot_b, plot = result["regionPolys"], result["rowH"], result["plotT"], result["plotB"], result["plot"]
    placed, moved, texts, label_boxes, cell_rect, to_cell = result["placed"], result["moved"], result["texts"], result["labelBoxes"], result["cellRect"], result["toCell"]
    placed.sort(key=lambda p: p["u"]["i"])

    # ---- bubbles, anchors
    bubbles: list[dict] = []
    for p in placed:
        u, spot = p["u"], p["spot"]
        b = {"x": spot["cx"], "y": spot["cy"], "r": u["r"], "cr": u["cr"], "shape": u["shape"], "tone": u["tone"], "hollow": u["hollow"], "cell": u["row"] * cols + u["col"], "label": u["item"]["label"]}
        if u["item"].get("id"):
            b["id"] = u["item"]["id"]
        bubbles.append(b)
    anchors: list[dict] = [{"id": p["u"]["item"]["id"], "x": p["spot"]["cx"] - p["u"]["cr"], "y": p["spot"]["cy"] - p["u"]["cr"], "w": 2 * p["u"]["cr"], "h": 2 * p["u"]["cr"]} for p in placed if p["u"]["item"].get("id")]

    # ---- arrows, then every item label that an arrow crosses looks for another side
    def end_of(e) -> dict:
        if not isinstance(e, str):
            t = to_cell(e[0], e[1])
            return {"x": t["x"], "y": t["y"], "cr": 0}
        i = next(idx for idx, it in enumerate(band["items"]) if it.get("id") == e)
        return {"x": bubbles[i]["x"], "y": bubbles[i]["y"], "cr": bubbles[i]["cr"]}

    arrows: list[dict] = []
    chips: list[dict] = []
    arrow_labels: list[dict] = []
    for a in band["arrows"]:
        p, q = end_of(a["from"]), end_of(a["to"])
        length = math.hypot(q["x"] - p["x"], q["y"] - p["y"])
        if length < p["cr"] + q["cr"] + 14:
            raise ValueError(f"quadrant(): the arrow {a['from'] if isinstance(a['from'], str) else 'from'} → {a['to'] if isinstance(a['to'], str) else 'to'} is too short to draw (the two ends are almost the same spot)")
        ux, uy = (q["x"] - p["x"]) / length, (q["y"] - p["y"]) / length
        s = {"x1": p["x"] + ux * (p["cr"] + 3), "y1": p["y"] + uy * (p["cr"] + 3), "x2": q["x"] - ux * (q["cr"] + 3), "y2": q["y"] - uy * (q["cr"] + 3)}
        arrows.append({**s, "dashed": a.get("dashed") or False, "tip": {"dx": ux, "dy": uy}})
        if a.get("label"):
            arrow_labels.append({"text": a["label"], "seg": len(arrows) - 1})
    if arrows:
        for pi, p in enumerate(placed):
            u, spot = p["u"], p["spot"]
            if not any(_segment_meets(a, spot["box"], 2) for a in arrows):
                continue
            others = [o for j, o in enumerate(placed) if j != pi]
            save = placed[:]
            placed[:] = others
            cands = [{"side": side, "box": result["labelAt"](u, side, spot["cx"], spot["cy"])} for side in _SIDES if side != spot["side"]]
            ok = next((cd for cd in cands if result["free"](u, spot["cx"], spot["cy"], cd["box"], [{"s": s} for s in arrows])), None)
            placed[:] = save
            if ok:
                placed[pi]["spot"] = {**spot, "side": ok["side"], "box": ok["box"]}

    # ---- item labels (after any move) and the arrow labels
    for pi, p in enumerate(placed):
        u, spot = p["u"], p["spot"]
        lb = result["labelAt"](u, spot["side"], spot["cx"], spot["cy"])
        for k, line in enumerate(u["lines"]):
            texts.append({"text": line, "x": lb["tx"], "y": lb["y"] + k * line_n + size, "anchor": lb["anchor"], "size": size, "bold": False, "fill": "text", "item": pi})
        label_boxes.append({"x": spot["box"]["x"], "y": spot["box"]["y"], "w": spot["box"]["w"], "h": spot["box"]["h"], "label": u["item"]["label"], "kind": "item", "item": pi})

    def chips_busy(r: dict) -> bool:
        if any(_circle_rect(p["spot"]["cx"], p["spot"]["cy"], p["u"]["cr"], r, 2) or _rects_meet(r, p["spot"]["box"], 2) for p in placed):
            return True
        if any(_rects_meet(r, o, 2) for o in chips):
            return True
        if any(_rects_meet(r, hd, 2) for hd in result["headers"]):
            return True
        return not _inside(r, result["inPlot"])

    for al in arrow_labels:
        s = arrows[al["seg"]]
        lw = tw(al["text"], size, 400)
        cw2, ch = lw + 10, size + 6
        chip = None
        for t in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8):
            r = {"x": s["x1"] + (s["x2"] - s["x1"]) * t - cw2 / 2, "y": s["y1"] + (s["y2"] - s["y1"]) * t - ch / 2, "w": cw2, "h": ch}
            x0, y0 = math.floor(r["x"] / 4) * 4, math.floor(r["y"] / 4) * 4
            snapped = {"x": x0, "y": y0, "w": math.ceil((r["x"] + r["w"]) / 4) * 4 - x0, "h": math.ceil((r["y"] + r["h"]) / 4) * 4 - y0}
            if not chips_busy(snapped):
                chip = snapped
                break
        if chip is None:
            raise ValueError(f"quadrant(): no room for the arrow label \"{al['text']}\" (shorten it, or move the items further apart)")
        chips.append(chip)
        texts.append({"text": al["text"], "x": chip["x"] + chip["w"] / 2, "y": chip["y"] + 3 + size - 1, "anchor": "middle", "size": size, "bold": False, "fill": "text"})
        label_boxes.append({**chip, "label": al["text"], "kind": "arrow"})

    # ---- cells, axis names
    cells = [{**cell_rect(k, r), "tone": cell.get("tone") or "plain"} for r, row_cells in enumerate(band["cells"]) for k, cell in enumerate(row_cells)]
    lines: list[dict] = []
    if band["crosshair"]:
        for k in range(1, cols):
            lines.append({"x1": plot_l + col_grid["x"][k], "y1": plot_t, "x2": plot_l + col_grid["x"][k], "y2": plot_b})
        acc = plot_t
        for r in range(rows - 1):
            acc += row_h[r]
            lines.append({"x1": plot_l, "y1": acc, "x2": plot_r, "y2": acc})

    def axis_box(text: str, sz: float, weight: float, anchor: str, ax: float, base: float) -> None:
        wd = tw(text, sz, weight)
        label_boxes.append({"x": ax - wd / 2 if anchor == "middle" else ax - wd if anchor == "end" else ax, "y": base - sz, "w": wd, "h": sz + 4, "label": text, "kind": "axis"})

    yx = plot_l - 10
    top_end = band["y"].get("low") if band["y"].get("reversed") else band["y"].get("high")
    bottom_end = band["y"].get("high") if band["y"].get("reversed") else band["y"].get("low")
    if top_end:
        texts.append({"text": top_end, "x": yx, "y": plot_t + size + 4, "anchor": "end", "size": size, "bold": False, "fill": "muted"})
        axis_box(top_end, size, 400, "end", yx, plot_t + size + 4)
    if bottom_end:
        texts.append({"text": bottom_end, "x": yx, "y": plot_b - 6, "anchor": "end", "size": size, "bold": False, "fill": "muted"})
        axis_box(bottom_end, size, 400, "end", yx, plot_b - 6)
    ty = (plot_t + plot_b) / 2 - (len(y_title) * line_t) / 2
    for k, line in enumerate(y_title):
        base = ty + k * line_t + t_size
        texts.append({"text": line, "x": yx, "y": base, "anchor": "end", "size": t_size, "bold": True, "fill": "text"})
        axis_box(line, t_size, 700, "end", yx, base)
    x_base = plot_b + 10 + size
    if x_left:
        texts.append({"text": x_left, "x": plot_l, "y": x_base, "anchor": "start", "size": size, "bold": False, "fill": "muted"})
        axis_box(x_left, size, 400, "start", plot_l, x_base)
    if x_right:
        texts.append({"text": x_right, "x": plot_r, "y": x_base, "anchor": "end", "size": size, "bold": False, "fill": "muted"})
        axis_box(x_right, size, 400, "end", plot_r, x_base)
    texts.append({"text": band["x"]["title"], "x": (plot_l + plot_r) / 2, "y": x_base, "anchor": "middle", "size": t_size, "bold": True, "fill": "text"})
    axis_box(band["x"]["title"], t_size, 700, "middle", (plot_l + plot_r) / 2, x_base)

    # ---- legends: the groups (shape + colour + name), then what the bubble area means
    marks: list[dict] = []
    cursor_y = _g4(x_base + 14)

    def legend_text(text: str, lx: float, ly: float, anchor: str = "start") -> None:
        texts.append({"text": text, "x": lx, "y": ly + size - 2, "anchor": anchor, "size": size, "bold": False, "fill": "text"})
        wd = tw(text, size, 400)
        label_boxes.append({"x": lx - wd if anchor == "end" else lx, "y": ly - 1, "w": wd, "h": size + 3, "label": text, "kind": "legend"})

    ly = cursor_y
    if band["groups"]:
        lx = plot_l
        for gi, g in enumerate(band["groups"]):
            need = 24 + tw(g, size, 400) + 20
            if lx > plot_l and lx + need > plot_r:
                lx, ly = plot_l, ly + 26
            gs = _group_style(gi)
            marks.append({"x": _g4(lx + 9), "y": ly + 8, "r": 7, "shape": gs["shape"], "tone": gs["tone"], "hollow": gs["hollow"], "ring": False})
            legend_text(g, lx + 22, ly)
            lx += need
        cursor_y = ly + 28
    if mx > 0:
        row_top_y = cursor_y
        refs = [{"v": v, "r": max(0.0, r_max * math.sqrt(v / mx))} for v in size_refs(mx)]
        refs = [rf for rf in refs if rf["r"] >= 5]
        title = _size_legend_title(band)
        lx = plot_l
        row_mid = _g4(row_top_y + max(r_max, size) + 2)
        legend_text(title, lx, row_mid - size / 2 - 1)
        lx += tw(title, size, 400) + 22
        for rf in refs:
            label = _size_ref_label(band, rf["v"])
            need = 2 * rf["r"] + 8 + tw(label, size, 400) + 22
            if lx + need - 22 > plot_r:
                break
            marks.append({"x": _g4(lx + rf["r"]), "y": _g4(row_mid), "r": rf["r"], "shape": "circle", "tone": "muted", "ring": True})
            legend_text(label, lx + 2 * rf["r"] + 8, row_mid - size / 2 - 1)
            lx += need
        cursor_y = row_mid + max(r_max, size) + 8
    h = cursor_y - y + _PAD - (6 if (mx > 0 or band["groups"]) else 14)

    taken = {b["cell"] for b in bubbles}
    allowed = band.get("allowEmpty")
    if allowed is True or band["regions"]:
        empty_cells: list[str] = []
    else:
        empty_cells = []
        for r, row_cells in enumerate(band["cells"]):
            for k, cell in enumerate(row_cells):
                if r * cols + k in taken or (allowed and any(c == k and rr == r for c, rr in allowed)):
                    continue
                empty_cells.append(f"{(cell['title'] + ' ') if cell.get('title') else ''}[{k}, {r}]")

    out: dict = {"type": "quadrant"}
    if band.get("id"):
        out["id"] = band["id"]
    out.update({"x": x, "y": y, "w": w, "h": h})
    if band.get("reveal") is not None:
        out["reveal"] = band["reveal"]
    if band.get("until") is not None:
        out["until"] = band["until"]
    out.update({"plot": plot, "crosshair": band["crosshair"], "cells": cells, "regions": region_polys, "lines": lines, "texts": texts, "bubbles": bubbles, "arrows": arrows, "chips": chips, "marks": marks, "anchors": anchors, "labelBoxes": label_boxes, "moved": moved, "floored": floored, "emptyCells": empty_cells})
    return out

# ---------------------------------------------------------------------------------------------------------------------------
# render (lib/emit-figures.ts's renderQuadrant())
# ---------------------------------------------------------------------------------------------------------------------------


def _shape_svg(shape: str, x: float, y: float, r: float, fill: str, stroke: str, sw: float, node: str | None = None) -> str:
    f = f'fill="{fill}" stroke="{stroke}" stroke-width="{js_num(sw)}"' + (f' data-node="{escape_attr(node)}"' if node else "")

    def n(v: float) -> str:
        return js_num(round1(v))

    if shape == "circle":
        return f'<circle cx="{n(x)}" cy="{n(y)}" r="{n(r)}" {f}/>'
    if shape == "square":
        s = r * math.sqrt(math.pi) / 2
        return f'<polygon points="{n(x - s)},{n(y - s)} {n(x + s)},{n(y - s)} {n(x + s)},{n(y + s)} {n(x - s)},{n(y + s)}" {f}/>'
    if shape == "diamond":
        s = r * math.sqrt(math.pi) / math.sqrt(2)
        return f'<polygon points="{n(x)},{n(y - s)} {n(x + s)},{n(y)} {n(x)},{n(y + s)} {n(x - s)},{n(y)}" {f}/>'
    a = r * math.sqrt(4 * math.pi / math.sqrt(3))
    hh = a * math.sqrt(3) / 2
    cy = y
    return f'<polygon points="{n(x)},{n(cy - hh * 2 / 3)} {n(x + a / 2)},{n(cy + hh / 3)} {n(x - a / 2)},{n(cy + hh / 3)}" {f}/>'


def _marker(shape: str, x: float, y: float, r: float, color: str, hollow: bool | None, node: str | None = None) -> str:
    """A hollow marker (groups 5 to 8) is an outline drawn inside the shape's area, so it is
    told from the filled ones by more than colour."""
    if hollow:
        return _shape_svg(shape, x, y, r - 1.5, PALETTE["bg"], color, 3, node)
    return _shape_svg(shape, x, y, r, color, PALETTE["bg"], 1.5, node)


def render_quadrant(b: dict, day: int | str = 1) -> str:
    """lib/emit-figures.ts:137-180 renderQuadrant()."""

    def ink(k: str, dim: bool = False) -> str:
        return PALETTE["muted"] if dim else color_of(k, day)

    out: list[str] = []
    for c in b["cells"]:
        ts = tone_style(c.get("tone"))
        fill = color_of(ts.fill, day)
        stroke = color_of(ts.fill, day) if ts.stroke is None else PALETTE["muted"] if c.get("tone") == "plain" else color_of(ts.stroke, day)
        x0, y0 = js_round(c["x"] / 4) * 4, js_round(c["y"] / 4) * 4
        x1, y1 = js_round((c["x"] + c["w"]) / 4) * 4, js_round((c["y"] + c["h"]) / 4) * 4
        dash = ' stroke-dasharray="6,4"' if ts.dashed else ""
        out.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="{0 if b["crosshair"] else 8}" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>')
    for r in b["regions"]:
        ts = tone_style(r.get("tone"))
        fill = color_of(ts.fill, day)
        stroke = color_of(ts.fill, day) if ts.stroke is None else PALETTE["muted"] if r.get("tone") == "plain" else color_of(ts.stroke, day)
        pts = " ".join(f"{js_round(px / 4) * 4},{js_round(py / 4) * 4}" for px, py in r["points"])
        dash = ' stroke-dasharray="6,4"' if ts.dashed else ""
        out.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="2" stroke-linejoin="round"{dash}/>')
    for l in b["lines"]:
        out.append(f'<path d="M{js_round(l["x1"] / 4) * 4},{js_round(l["y1"] / 4) * 4} L{js_round(l["x2"] / 4) * 4},{js_round(l["y2"] / 4) * 4}" fill="none" stroke="{PALETTE["muted"]}" stroke-width="2"/>')

    def head(x: float, y: float, dx: float, dy: float, color: str) -> str:
        length, width = 10, 5
        pts = [(x, y), (x - dx * length - dy * width, y - dy * length + dx * width), (x - dx * length + dy * width, y - dy * length - dx * width)]
        return f'<polygon points="{" ".join(f"{js_round(a)},{js_round(c)}" for a, c in pts)}" fill="{color}"/>'

    for a in b["arrows"]:
        dash = ' stroke-dasharray="6,4"' if a.get("dashed") else ""
        out.append(f'<path d="M{js_round(a["x1"])},{js_round(a["y1"])} L{js_round(a["x2"])},{js_round(a["y2"])}" fill="none" stroke="{PALETTE["text"]}" stroke-width="2"{dash}/>')
        out.append(head(a["x2"], a["y2"], a["tip"]["dx"], a["tip"]["dy"], PALETTE["text"]))
    for c in b["chips"]:
        out.append(f'<rect x="{c["x"]}" y="{c["y"]}" width="{c["w"]}" height="{c["h"]}" rx="4" fill="{PALETTE["bg"]}"/>')
    for q in b["bubbles"]:
        out.append(_marker(q["shape"], q["x"], q["y"], q["r"], ink(q["tone"], q.get("dim", False)), q.get("hollow"), q.get("dataNode")))
    for m in b["marks"]:
        if m.get("ring"):
            out.append(_shape_svg(m["shape"], m["x"], m["y"], m["r"], "none", ink(m["tone"], b.get("dim", False)), 2))
        else:
            out.append(_marker(m["shape"], m["x"], m["y"], m["r"], ink(m["tone"], b.get("dim", False)), m.get("hollow")))
    for t in b["texts"]:
        dim = b.get("dim", False) or (t.get("item") is not None and b["bubbles"][t["item"]].get("dim", False))
        anchor = "" if t["anchor"] == "start" else f' text-anchor="{t["anchor"]}"'
        weight = ' font-weight="700"' if t.get("bold") else ""
        node = f' data-node="{escape_attr(t["dataNode"])}"' if t.get("dataNode") else ""
        out.append(f'<text x="{js_round(t["x"])}" y="{js_round(t["y"])}"{anchor} font-size="{t["size"]}"{weight} fill="{ink(t["fill"], dim)}"{node}>{emoji_span(t["text"])}</text>')
    return "\n  ".join(out)
