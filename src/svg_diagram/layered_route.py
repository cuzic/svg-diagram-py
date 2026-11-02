"""1:1 port of lib/layered-route.ts — orthogonal routing of the edges of a layered layout
(graph_layout.py's layout_layered()), shared by states()/classes()/cause()/pert()/
causalLoop()/dependencyNetwork() (none of those bands are wired to this module yet — see
BANDS.md's Tier 3 note; this port is the engine only).

Everything here is in the layout's own ('right') axes: layers run along x. `place` moves a
point of those axes into the figure (and transposes it for a 'down' diagram).

Depends on already-ported graph_layout.layout_layered(), polyline_metrics.py (simplify/
bends_of/crossings_of/crossings_with/score_of/runs_together), route_apart.move_apart(),
route_search.{head_crossings, search_route}.

Golden master: lib/layered-route.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import cmp_to_key

from .emit_common import js_round
from .graph_layout import layout_layered
from .polyline_metrics import bends_of, crossings_of, crossings_with, runs_together, score_of, simplify
from .route_apart import move_apart
from .route_search import head_crossings, search_route

STUB = 18
LANE = 14


def stub_of(space: float = 1) -> float:
    """lib/layered-route.ts:19 stubOf()."""
    return js_round(STUB * space)


def lane_step_of(space: float = 1) -> float:
    """lib/layered-route.ts:20 laneStepOf()."""
    return js_round(LANE * space)


def gap_for(n: int, chip: float = 0, space: float = 1) -> float:
    """lib/layered-route.ts:18 gapFor(): the gap two layers need so that `n` direct arrows
    through it each get a lane (and a label chip beside them has room)."""
    return max(2 * stub_of(space) + lane_step_of(space) * max(0, n - 1) + js_round(16 * space), chip + stub_of(space) + 26)


def elbows(pts: list[dict], turn: float | None = None, last_turn: float | None = None) -> list[dict]:
    """lib/layered-route.ts:27-38 elbows(): horizontal-vertical-horizontal elbows through the
    points (the layer axis is x here). A direct arrow turns at `turn` (an x in the gap between
    its two layers); the others turn half-way between their points."""
    out: list[dict] = pts[:1]
    for i in range(len(pts) - 1):
        p, q = pts[i], pts[i + 1]
        if p["y"] != q["y"]:
            if len(pts) == 2 and turn is not None:
                mx = turn
            elif i + 2 == len(pts) and last_turn is not None:
                mx = last_turn
            else:
                mx = (p["x"] + q["x"]) / 2
            out.append({"x": mx, "y": p["y"]})
            out.append({"x": mx, "y": q["y"]})
        out.append(q)
    return simplify(out)


def corridor_load(lay: dict) -> int:
    """lib/layered-route.ts:409-426 corridorLoad(): the most direct arrows that pass through
    one gap between two layers (each needs its own lane there)."""
    load: dict[str, int] = {}
    for e in lay["edges"]:
        if e.get("self") or len(e["points"]) != 2:
            continue
        a, b = lay["nodes"][e["from"]], lay["nodes"][e["to"]]
        k = f"{js_round(min(a['x'] + a['w'] / 2, b['x'] + b['w'] / 2))}:{js_round(max(a['x'] + a['w'] / 2, b['x'] + b['w'] / 2))}"
        load[k] = load.get(k, 0) + 1
    direct: dict[int, int] = {}
    outer_in: dict[int, int] = {}
    for e in lay["edges"]:
        if e.get("self"):
            continue
        l1, l2 = lay["layers"][e["from"]], lay["layers"][e["to"]]
        if e.get("outer"):
            for g in (l1 - 1, l2):
                outer_in[g] = outer_in.get(g, 0) + 1
        elif len(e["points"]) == 2:
            lo = min(l1, l2)
            direct[lo] = direct.get(lo, 0) + 1
    candidates = [1, *load.values(), *(n + direct.get(g, 0) for g, n in outer_in.items())]
    return max(candidates)


def layout_with_lanes(nodes: list[dict], edges: list[dict], opts: dict, chip: float = 0, space: float = 1) -> dict:
    """lib/layered-route.ts:432-436 layoutWithLanes(): layout_layered, with the gap between
    layers wide enough for the arrows that share it: laid out once to see how many arrows go
    through each gap (layers do not depend on the gap), then again with a gap that gives each
    its own lane."""
    first = layout_layered(nodes, edges, opts)
    need = gap_for(corridor_load(first), chip, space)
    return layout_layered(nodes, edges, {**opts, "levelGap": need}) if need > opts.get("levelGap", 0) else first


def _along_each(routes: dict[int, list[dict]]) -> int:
    """lib/layered-route.ts:42-47 alongEach(): the pairs of arrows with runs along one line
    (they read as one) — what spreading the lanes is for, so it may not make more."""
    segs = [[{"p": r[k], "q": r[k + 1]} for k in range(len(r) - 1)] for r in routes.values()]
    n = 0
    for x, sx in enumerate(segs):
        for sy in segs[x + 1 :]:
            if any(runs_together(u, v) for u in sx for v in sy):
                n += 1
    return n


def route_layered(
    lay: dict,
    place: Callable[[dict], dict],
    port_step: float = 14,
    group_of: Callable[[int], int | None] | None = None,
    round_: Callable[[str], bool] | None = None,
    straighten: bool = True,
    lane_share: bool = False,
    aside: bool = False,
    detour: bool = False,
    lone_ports: bool | None = None,
    space: float = 1,
    lane_heads: bool = False,
) -> dict[int, list[dict]]:
    """lib/layered-route.ts:53-58 routeLayered(): routeOnce twice — with the lanes of a gap at
    the fixed step, and spread over the room the gap has (`laneIn`). The spread routes are
    kept only when (crossings, bends) is no worse: the order of the lanes is the same, but
    where they sit decides which runs cross."""
    if lone_ports is None:
        lone_ports = detour
    fixed = _route_once(lay, place, port_step, group_of, round_, straighten, lane_share, aside, detour, lone_ports, space, lane_heads, False)
    spread = _route_once(lay, place, port_step, group_of, round_, straighten, lane_share, aside, detour, lone_ports, space, lane_heads, True)
    a, b = score_of(list(fixed.values())), score_of(list(spread.values()))
    if b["crossings"] <= a["crossings"] and b["bends"] <= a["bends"] and _along_each(spread) <= _along_each(fixed):
        return spread
    return fixed


def _route_once(
    lay: dict,
    place: Callable[[dict], dict],
    port_step: float,
    group_of: Callable[[int], int | None] | None,
    round_: Callable[[str], bool] | None,
    straighten: bool,
    lane_share: bool,
    aside: bool,
    detour: bool,
    lone_ports: bool,
    space: float,
    lane_heads: bool,
    spread: bool,
) -> dict[int, list[dict]]:
    """lib/layered-route.ts:67-406 routeOnce(): the polyline of every non-self edge (by its
    index in lay["edges"]), from the tail's box edge to the head's.

    ports: the edges that meet one side of a box fan out along it (ordered by where the other
    end is, so they do not cross); lanes: direct arrows through one gap between two layers
    take separate vertical runs. straightening (ADR 0016 D3): a direct arrow whose two boxes
    overlap across the layer axis becomes one straight line when that does not make the
    drawing worse; `round_` names the nodes that are not rectangles (a circle, a hexagon),
    whose arrows keep to the middle of the side.

    Node inlines this whole algorithm into one ~340-line function (routeOnce is not exported,
    so it can only be golden-tested as a black box through route_layered() above); this port
    decomposes it into named nested helpers, one per ADR 0016 pass (see layered_route.py's
    module docstring / BANDS.md for the pass -> ADR number mapping), purely for this port's
    own maintainability — Node's single-function shape is an accident of the source file, not
    a contract. A couple of cheap, targeted self-consistency assertions are kept at the
    riskiest mutate-and-restore boundaries (D3's align()/undo(), the `spread` respread's
    rollback) since a golden test on the *final* routes alone cannot tell whether an
    intermediate restore left stray state that happened not to affect this particular input.
    """
    stub, lane = stub_of(space), lane_step_of(space)  # this figure's stub and lane step (shadow the module's STUB/LANE, same as Node — ADR 0036 D2)

    def edge_at(i: int) -> dict:
        return lay["edges"][i]

    def node_of(node_id: str) -> dict:
        return lay["nodes"][node_id]

    def layer_of(node_id: str) -> int:
        return lay["layers"][node_id]

    def lane_y(i: int) -> float:
        return edge_at(i)["points"][1]["y"]

    port_of: dict[str, float] = {}
    lane_of: dict[int, float] = {}
    slot_of: dict[str, dict] = {}

    # the gap between layer l and l+1 runs from the right edge of the widest box of l to the left edge of the leftmost box of l+1
    layer_right: dict[int, float] = {}
    layer_left: dict[int, float] = {}
    for node_id, n in lay["nodes"].items():
        l = layer_of(node_id)
        layer_right[l] = max(layer_right.get(l, -math.inf), n["x"] + n["w"])
        layer_left[l] = min(layer_left.get(l, math.inf), n["x"])

    # laneHeads: a return in an outer lane ends on the face of its head that looks at the lane (the bottom or the top), not on the head's
    # right side, where it would cross the arrows that leave that side. Only where the run from the lane to the face passes no other box.
    face_of: dict[int, dict] = {}
    if lane_heads:
        by_face: dict[str, list[int]] = {}
        for i, e in enumerate(lay["edges"]):
            if e.get("self") or not e.get("outer"):
                continue
            if any(other.get("self") and other["from"] == e["to"] for other in lay["edges"]):
                continue
            b = node_of(e["to"])
            key = f"{e['to']}:{'b' if lane_y(i) > b['y'] + b['h'] / 2 else 't'}"
            by_face.setdefault(key, []).append(i)
        for lst in by_face.values():
            b = node_of(edge_at(lst[0])["to"])
            lane0 = lane_y(lst[0])
            y = b["y"] + b["h"] if lane0 > b["y"] + b["h"] / 2 else b["y"]
            step = min(port_step, (b["w"] - 12) / (len(lst) - 1)) if len(lst) > 1 else 0
            # the tails are on the far side of the head, so the lane nearest the head takes the place nearest them (the right): a
            # farther lane's vertical run then never crosses a nearer lane's run
            order = sorted(lst, key=lambda p: (abs(lane_y(p) - y), p))
            for k, i in enumerate(order):
                x = b["x"] + b["w"] / 2 + ((len(order) - 1) / 2 - k) * step
                lane_i = lane_y(i)
                lo, hi = min(lane_i, y), max(lane_i, y)
                blocked = any(
                    node_id != edge_at(i)["to"] and n["x"] - 0.5 < x < n["x"] + n["w"] + 0.5 and n["y"] - 0.5 < hi and lo < n["y"] + n["h"] + 0.5
                    for node_id, n in lay["nodes"].items()
                )
                if blocked:
                    continue
                face_of[i] = {"x": x, "y": y}

    # The step between the lanes of one gap: the lanes of a gap are counted from its sides at `lane` apart, which leaves a gap wider than
    # they need with its lanes crowded at the sides. They spread over the room the gap has left, up to twice the step; a gap with no room
    # keeps `lane`. Direct arrows, the long arrows into an AND and the turns of the returns in an outer lane all use the step of their
    # gap, so their order and the way they share the gap do not change.
    def level(i: int) -> bool:
        # a direct arrow whose two ports are at one height is a straight line: it has no vertical run, so it takes no lane (without
        # `spread` the lanes are the old ones: every direct arrow has one)
        if not spread:
            return False
        e = edge_at(i)
        a, b = node_of(e["from"]), node_of(e["to"])
        return abs(a["y"] + a["h"] / 2 + port_of.get(f"{i}:0", 0) - (b["y"] + b["h"] / 2 + port_of.get(f"{i}:1", 0))) < 0.5

    crowded: dict[int, int] | None = None

    def crowd_of() -> dict[int, int]:
        nonlocal crowded
        if crowded is not None:
            return crowded
        crowd: dict[int, int] = {}
        crowded = crowd
        for i, e in enumerate(lay["edges"]):
            if e.get("self"):
                continue
            l1, l2 = layer_of(e["from"]), layer_of(e["to"])
            if e.get("outer"):
                gs = [l1 - 1, l2]
            elif len(e["points"]) == 2:
                gs = [] if level(i) else [min(l1, l2)]
            elif l1 < l2 and group_of:
                gs = [l2 - 1]
            else:
                gs = []
            for g in gs:
                crowd[g] = crowd.get(g, 0) + 1
        return crowd

    def lane_in(g: int) -> float:
        n = crowd_of().get(g, 0)
        gl, gr = layer_right.get(g), layer_left.get(g + 1)
        if not spread or n < 2 or gl is None or gr is None:
            return lane
        return min(2 * lane, max(lane, math.floor((gr - gl - 2 * stub - js_round(16 * space)) / (n - 1))))

    ends: list[dict] = []
    corridors: dict[str, list[int]] = {}
    for i, e in enumerate(lay["edges"]):
        if e.get("self"):
            continue
        a, b = node_of(e["from"]), node_of(e["to"])
        ca = {"x": a["x"] + a["w"] / 2, "y": a["y"] + a["h"] / 2}
        cb = {"x": b["x"] + b["w"] / 2, "y": b["y"] + b["h"] / 2}
        pts = e["points"]
        first = pts[1] if len(pts) > 1 else cb
        last = pts[-2] if len(pts) > 1 else ca
        ends.append({"key": f"{e['from']}:{'r' if first['x'] >= ca['x'] else 'l'}", "edge": i, "end": 0, "other": first["y"]})
        if i not in face_of:
            ends.append({"key": f"{e['to']}:{'l' if last['x'] <= cb['x'] else 'r'}", "edge": i, "end": 1, "other": last["y"]})
        if len(pts) == 2:  # direct arrows through one gap between two layers, in groups that go down / go up
            k = f"{js_round(min(ca['x'], cb['x']))}:{js_round(max(ca['x'], cb['x']))}"
            corridors.setdefault(k, []).append(i)

    by_key: dict[str, list[dict]] = {}
    for en in ends:
        by_key.setdefault(en["key"], []).append(en)
    for lst in by_key.values():
        # the arrows of one group (an AND) arrive side by side: they sort by where the group as a whole comes from, then among themselves
        mean: dict[int, float] = {}
        count: dict[int, int] = {}
        if group_of:
            for en in lst:
                g = group_of(en["edge"]) if en["end"] == 1 else None
                if g is not None:
                    mean[g] = mean.get(g, 0) + en["other"]
                    count[g] = count.get(g, 0) + 1
            for g, cnt in count.items():
                mean[g] = mean[g] / cnt

        def key_of(en: dict) -> float:
            if en["end"] == 1 and group_of and group_of(en["edge"]) is not None:
                return mean[group_of(en["edge"])]
            return en["other"]

        # NOT decomposable into a per-element sort key: the second tie-break term reads `p.end` only and unconditionally subtracts
        # `groupOf(q.edge)`, so comparing (p, q) and (q, p) need not negate each other when p.end != q.end (a box side can mix tail
        # ends and head ends of different edges). Port the 2-argument comparator directly via cmp_to_key rather than risk a Python
        # sort disagreeing with V8's on exactly the pairs this asymmetry affects.
        def cmp(p: dict, q: dict) -> int:
            d = key_of(p) - key_of(q)
            if d != 0:
                return -1 if d < 0 else 1
            if p["end"] == 1 and group_of:
                gp, gq = group_of(p["edge"]), group_of(q["edge"])
                d2 = (gp if gp is not None else -1) - (gq if gq is not None else -1)
            else:
                d2 = 0
            if d2 != 0:
                return -1 if d2 < 0 else 1
            d3 = p["other"] - q["other"]
            if d3 != 0:
                return -1 if d3 < 0 else 1
            return p["edge"] - q["edge"]

        lst.sort(key=cmp_to_key(cmp))
        for k, en in enumerate(lst):
            e = edge_at(en["edge"])
            node_id = e["from"] if en["end"] == 0 else e["to"]
            h = node_of(node_id)["h"]
            step = min(port_step, (h - 12) / (len(lst) - 1)) if len(lst) > 1 else 0
            # the ports of one side keep an even step (a tail and a head on one side are never closer than a step). The ports of every
            # box's left side sit half a step lower than those of its right side: a tail port of one box and a head port of the next
            # (same layer pair) otherwise share a height and their runs line up as one line. A lone port stays in the middle (a
            # straight arrow stays straight).
            room = h / 2 - 6
            span = (len(lst) - 1) / 2 * step
            slack = min(step / 2, room - span)
            lower = slack if en["key"].endswith(":l") and len(lst) > 1 and slack >= 3 else 0
            port_of[f"{en['edge']}:{en['end']}"] = (k - (len(lst) - 1) / 2) * step + lower
            slot_of[f"{en['edge']}:{en['end']}"] = {"list": lst, "k": k, "step": step}

    # fan-out (one tail): the arrow that goes farthest turns first (the lane nearest the tail), so no vertical run crosses another
    # arrow's last run. fan-in (one head, several tails): the other way round, the nearest tail turns first.
    def dy(i: int) -> float:
        e = edge_at(i)
        a, b = node_of(e["from"]), node_of(e["to"])
        return abs((b["y"] + b["h"] / 2) - (a["y"] + a["h"] / 2))

    # arrows that go down and arrows that go up through the same gap are told apart too: the up group takes the lanes after the down group's
    def goes_down(i: int) -> bool:
        e = edge_at(i)
        a, b = node_of(e["from"]), node_of(e["to"])
        return b["y"] + b["h"] / 2 >= a["y"] + a["h"] / 2

    # forward arrows (tail in the earlier layer) take lanes counted from the gap's left side, backward arrows (a return) from its right
    # side, so the two kinds never land on one lane (the gap is sized for all of them together, see gap_for)
    def forward(i: int) -> bool:
        e = edge_at(i)
        return layer_of(e["from"]) < layer_of(e["to"])

    # ADR 0016 D11: a long arrow into a grouped head (an AND) takes the first lanes of the gap before the head, so its last turn lies on
    # the tail side of the direct arrows' turns and the two never run side by side; the direct arrows' lanes come after. Only when asked
    # (the caller keeps it when the figure gets no worse).
    long_lane: dict[int, int] = {}
    long_in: dict[int, int] = {}
    if lane_share and group_of:
        for i, e in enumerate(lay["edges"]):
            if e.get("self") or len(e["points"]) <= 2 or group_of(i) is None or not forward(i):
                continue
            lo = layer_of(e["to"]) - 1
            k = long_in.get(lo, 0)
            long_in[lo] = k + 1
            long_lane[i] = k

    def assign_lanes() -> None:
        lane_of.clear()
        for all0 in corridors.values():
            all_ = [i for i in all0 if not level(i)]
            if not all_:
                continue
            gap_of = min(layer_of(edge_at(all_[0])["from"]), layer_of(edge_at(all_[0])["to"]))
            for group in ([i for i in all_ if forward(i)], [i for i in all_ if not forward(i)]):
                k = long_in.get(gap_of, 0) if group and forward(group[0]) else 0
                for lst in ([i for i in group if goes_down(i)], [i for i in group if not goes_down(i)]):
                    fan_in = len({edge_at(i)["to"] for i in lst}) == 1 and len({edge_at(i)["from"] for i in lst}) > 1
                    for i in sorted(lst, key=lambda p: (dy(p) if fan_in else -dy(p), p)):
                        lane_of[i] = k * lane_in(gap_of)
                        k += 1

    assign_lanes()

    # returns in an outer lane (graph_layout.py's `outer`): each turns in the gap before its tail's layer and in the gap after its
    # head's layer, past the lanes of the direct arrows there (a tail counts from the gap's right side, a head from its left side)
    gap_back: dict[int, int] = {}
    gap_fwd: dict[int, int] = {}
    tail_at: dict[int, int] = {}
    head_at: dict[int, int] = {}
    outer_turns: dict[int, dict] = {}

    def turn_outer() -> None:
        tail_at.clear()
        head_at.clear()
        gap_back.clear()
        gap_fwd.clear()
        for i, e in enumerate(lay["edges"]):  # the direct arrows that have a lane there now (counted again whenever the lanes are laid again)
            if e.get("self") or len(e["points"]) != 2 or level(i):
                continue
            l1, l2 = layer_of(e["from"]), layer_of(e["to"])
            g = min(l1, l2)
            m = gap_fwd if l1 < l2 else gap_back
            m[g] = m.get(g, 0) + 1

        def within(g: int, x: float, head: bool = False) -> float:  # a turn stays inside its gap; the last run into a head keeps room for the arrowhead
            if not spread:
                return x
            gl, gr = layer_right.get(g), layer_left.get(g + 1)
            if gl is None or gr is None:
                return x
            return min(gr - stub, max(gl + (max(stub, 22) if head else stub), x))

        for i, e in enumerate(lay["edges"]):
            if not e.get("outer"):
                continue
            gt, gh = layer_of(e["from"]) - 1, layer_of(e["to"])
            kt, kh = tail_at.get(gt, 0), head_at.get(gh, 0)
            tail_at[gt], head_at[gh] = kt + 1, kh + 1
            outer_turns[i] = {
                "tail": within(gt, layer_left.get(gt + 1, 0) - stub - (gap_back.get(gt, 0) + kt) * lane_in(gt)),
                "head": within(gh, layer_right.get(gh, 0) + stub + (gap_fwd.get(gh, 0) + kh) * lane_in(gh), True),
            }

    turn_outer()

    # the routes for the ports as they stand (in the layout's own axes)
    shift_of: dict[int, float] = {}  # a long arrow's way points moved across the layers (ADR 0016 D12)
    turn_at: dict[int, float] = {}  # a direct arrow's turn moved to another x in its gap (ADR 0016 D13)
    detours: dict[int, list[dict]] = {}  # a long arrow's route found by searching around the boxes (`detour`): kept when the routes are built again

    def build() -> dict[int, list[dict]]:
        out: dict[int, list[dict]] = {}
        long_into: dict[str, int] = {}  # long arrows into one head, each with its own last turn
        for i, e in enumerate(lay["edges"]):
            if e.get("self"):
                continue
            a, b = node_of(e["from"]), node_of(e["to"])
            ca = {"x": a["x"] + a["w"] / 2, "y": a["y"] + a["h"] / 2}
            cb = {"x": b["x"] + b["w"] / 2, "y": b["y"] + b["h"] / 2}
            pts = e["points"]
            first = pts[1] if len(pts) > 1 else cb
            last = pts[-2] if len(pts) > 1 else ca
            start = {"x": a["x"] + a["w"] if first["x"] >= ca["x"] else a["x"], "y": ca["y"] + port_of.get(f"{i}:0", 0)}
            end = {"x": b["x"] if last["x"] <= cb["x"] else b["x"] + b["w"], "y": cb["y"] + port_of.get(f"{i}:1", 0)}
            turns = outer_turns.get(i)
            if turns:  # out of the tail's left side, out to the lane, back along it, into the head's right side (or up into its face, see lane_heads)
                lane_y_i = lane_y(i)
                face = face_of.get(i)
                if face:
                    out[i] = simplify([start, {"x": turns["tail"], "y": start["y"]}, {"x": turns["tail"], "y": lane_y_i}, {"x": face["x"], "y": lane_y_i}, face])
                    continue
                out[i] = simplify(
                    [start, {"x": turns["tail"], "y": start["y"]}, {"x": turns["tail"], "y": lane_y_i}, {"x": turns["head"], "y": lane_y_i}, {"x": turns["head"], "y": end["y"]}, end]
                )
                continue
            # a direct arrow turns in a lane: a place in the gap between its two layers (from the left side for a forward arrow, from
            # the right side for a return), whatever the widths of the boxes it leaves and enters
            turn: float | None = None
            if len(pts) == 2:
                lo = min(layer_of(e["from"]), layer_of(e["to"]))
                gl = layer_right[lo]
                gr = layer_left.get(lo + 1, gl + 2 * stub)
                gw = gr - gl
                d = min(stub + lane_of.get(i, 0), max(gw / 2, gw - 22))  # the last run keeps room for the arrowhead
                turn = turn_at.get(i, gl + d if forward(i) else gr - d)
            # a long arrow into a grouped head (an AND) makes its last turn a fixed distance before the head, clear of the lanes of the
            # direct arrows (which are counted from the gap's left side), so the two kinds never run side by side
            last_turn: float | None = None
            if group_of and len(pts) > 2 and forward(i):
                lo = layer_of(e["to"]) - 1
                gl, gr = layer_right.get(lo), layer_left.get(lo + 1)
                if gl is not None and gr is not None:
                    k = long_into.get(e["to"], 0)
                    long_into[e["to"]] = k + 1
                    if lane_share and i in long_lane:
                        last_turn = min(gr - 26, gl + stub + long_lane[i] * lane_in(lo))
                    else:
                        last_turn = max(gl + stub, gr - 26 - k * lane_in(lo))
            dz = shift_of.get(i, 0)
            found = detours.get(i)
            if found is not None:
                out[i] = [start, *found[1:-1], end]
            else:
                mid = [({"x": p["x"], "y": p["y"] + dz} if dz else p) for p in pts[1:-1]]
                out[i] = elbows([start, *mid, end], turn, last_turn)
        return out

    # ADR 0016 D3: an arrow between two boxes that overlap along the layer's cross axis becomes one straight line, when its two ports
    # can be moved to one height. Each candidate is tried against the whole drawing and kept only if (crossings, bends) get strictly
    # better and the new straight run does not lie along another arrow's run, so a figure never gets worse.
    def centre_y(node_id: str) -> float:
        n = node_of(node_id)
        return n["y"] + n["h"] / 2

    def end_y(i: int, end: int) -> float:
        e = edge_at(i)
        return centre_y(e["from"] if end == 0 else e["to"]) + port_of.get(f"{i}:{end}", 0)

    def pair_of(i: int) -> str:
        e = edge_at(i)
        return str(min(layer_of(e["from"]), layer_of(e["to"])))

    def align(i: int) -> Callable[[], None] | None:
        """Moves both ports of arrow `i` to one height; returns how to take it back, or None
        when no such height exists."""
        e = edge_at(i)
        a, b = node_of(e["from"]), node_of(e["to"])
        ya, yb = end_y(i, 0), end_y(i, 1)
        if abs(ya - yb) < 0.5:
            return None
        # (1) both boxes reach this height, 6px inside their edges (the same margin as the ports'); (2) the neighbours on each side keep a step
        lo = max(a["y"], b["y"]) + 6
        hi = min(a["y"] + a["h"], b["y"] + b["h"]) - 6
        for end in (0, 1):
            slot = slot_of[f"{i}:{end}"]

            def near(k: int, slot: dict = slot) -> float | None:
                lst = slot["list"]
                if 0 <= k < len(lst):
                    o = lst[k]
                    return end_y(o["edge"], o["end"])
                return None

            prev, nxt = near(slot["k"] - 1), near(slot["k"] + 1)
            if prev is not None:
                lo = max(lo, prev + slot["step"])
            if nxt is not None:
                hi = min(hi, nxt - slot["step"])
        if lo > hi:
            return None
        y = min(hi, max(lo, (ya + yb) / 2))
        # (3) no other arrow of this pair of layers has a port at this height (their runs would line up as one line)
        own = {f"{i}:0", f"{i}:1"}
        for j, o in enumerate(lay["edges"]):
            if j == i or o.get("self") or pair_of(j) != pair_of(i):
                continue
            for end in (0, 1):
                if f"{j}:{end}" not in own and abs(end_y(j, end) - y) < 3:
                    return None
        was = [port_of.get(f"{i}:0"), port_of.get(f"{i}:1")]
        port_of[f"{i}:0"] = y - centre_y(e["from"])
        port_of[f"{i}:1"] = y - centre_y(e["to"])

        def undo() -> None:
            for end in (0, 1):
                if was[end] is None:
                    port_of.pop(f"{i}:{end}", None)
                else:
                    port_of[f"{i}:{end}"] = was[end]

        return undo

    def along_other(routes: dict[int, list[dict]], i: int) -> bool:
        """Does the straight run of arrow `i` lie along a horizontal run of another arrow
        (within 3px, sharing more than a point)?"""
        r = routes[i]
        if len(r) != 2:
            return False
        r0, r1 = r[0], r[1]
        lo, hi = min(r0["x"], r1["x"]), max(r0["x"], r1["x"])
        for j, p in routes.items():
            if j == i:
                continue
            for k in range(1, len(p)):
                a, b = p[k - 1], p[k]
                if b["y"] == a["y"] and abs(b["y"] - r0["y"]) < 3 and min(hi, max(b["x"], a["x"])) - max(lo, min(b["x"], a["x"])) > 1:
                    return True
        return False

    routes = build()

    def is_direct_candidate(i: int) -> bool:
        e = edge_at(i)
        if not (straighten and not e.get("self") and not e.get("outer") and len(e["points"]) == 2):
            return False
        if group_of and group_of(i) is not None:
            return False
        if round_ and (round_(e["from"]) or round_(e["to"])):
            return False
        return lone_ports or len(slot_of[f"{i}:0"]["list"]) > 1 or len(slot_of[f"{i}:1"]["list"]) > 1

    direct = [i for i in range(len(lay["edges"])) if is_direct_candidate(i)]
    best = score_of(list(routes.values()))
    for i in direct:
        port_snapshot = dict(port_of)
        undo = align(i)
        if undo is None:
            continue
        trial = build()
        score = score_of(list(trial.values()))
        better = score["crossings"] < best["crossings"] or (score["crossings"] == best["crossings"] and score["bends"] < best["bends"])
        if better and not along_other(trial, i):
            routes = trial
            best = score
        else:
            undo()
            assert port_of == port_snapshot, f"routeOnce: align()/undo() left port_of inconsistent for edge {i}"

    # the arrows that became straight lines no longer take a lane: the others take their lanes again, over the room that is left
    if spread:
        lanes_snapshot = dict(lane_of)
        turns_snapshot = dict(outer_turns)
        before_crowded = crowded

        # how many arrows run through a box that is not one of their two ends: the new lanes may not add to them
        def pierced(m: dict[int, list[dict]]) -> int:
            total = 0
            for i, r in m.items():
                e = edge_at(i)
                for node_id, n in lay["nodes"].items():
                    if node_id == e["from"] or node_id == e["to"]:
                        continue
                    for k in range(1, len(r)):
                        p, q = r[k - 1], r[k]
                        if max(p["x"], q["x"]) > n["x"] + 1 and min(p["x"], q["x"]) < n["x"] + n["w"] - 1 and max(p["y"], q["y"]) > n["y"] + 1 and min(p["y"], q["y"]) < n["y"] + n["h"] - 1:
                            total += 1
                            break
            return total

        pierced_before = pierced(routes)
        crowded = None
        assign_lanes()
        turn_outer()
        trial = build()
        score = score_of(list(trial.values()))
        if score["crossings"] <= best["crossings"] and score["bends"] <= best["bends"] and pierced(trial) <= pierced_before:
            routes = trial
            best = score
        else:
            crowded = before_crowded
            lane_of.clear()
            lane_of.update(lanes_snapshot)
            outer_turns.clear()
            outer_turns.update(turns_snapshot)
            assert lane_of == lanes_snapshot and outer_turns == turns_snapshot, "routeOnce: spread rollback left lane_of/outer_turns inconsistent"

    # a long arrow (it passes a layer between its two ends) takes the way around the boxes with the fewest bends when that is strictly
    # better in (crossings, bends): its way points are the middle of each layer's gap, which can send it far out and back
    if detour:
        rects = [{"x": n["x"], "y": n["y"], "w": n["w"], "h": n["h"]} for n in lay["nodes"].values()]
        bounds = {"x": 0, "y": 0, "w": lay["w"], "h": lay["h"]}
        # the arrows into a grouped head (an AND) must not cross each other more than they did (an AND arc over crossing arrows reads wrongly: ADR 0015)
        heads: set[str] = set()
        for i, e in enumerate(lay["edges"]):
            if not e.get("self") and group_of and group_of(i) is not None:
                heads.add(e["to"])

        def and_cross(m: dict[int, list[dict]]) -> int:
            if not heads:
                return 0
            return crossings_of([pts for j, pts in m.items() if edge_at(j)["to"] in heads])

        def touches(i: int, r: list[dict]) -> bool:
            """Does a run of the route lie on a box that is not one of the arrow's two ends?"""
            e = edge_at(i)
            for node_id, n in lay["nodes"].items():
                if node_id == e["from"] or node_id == e["to"]:
                    continue
                for k in range(1, len(r)):
                    p, q = r[k - 1], r[k]
                    if max(p["x"], q["x"]) > n["x"] - 0.5 and min(p["x"], q["x"]) < n["x"] + n["w"] + 0.5 and max(p["y"], q["y"]) > n["y"] - 0.5 and min(p["y"], q["y"]) < n["y"] + n["h"] + 0.5:
                        return True
            return False

        head_cross = head_crossings(list(routes.values()))
        and_now = and_cross(routes)
        for i, e in enumerate(lay["edges"]):
            r = routes.get(i)
            if r is None or e.get("self") or e.get("outer") or len(e["points"]) <= 2 or (group_of and group_of(i) is not None) or r[-1]["x"] <= r[0]["x"]:
                continue
            # only an arrow that bends 3 times or more can get much better; one that runs along a box it should clear is searched whatever it bends
            on_box = touches(i, r)
            if len(r) <= 4 and not on_box:
                continue
            rest = [pts for j, pts in routes.items() if j != i]
            found = search_route(r[0], r[-1], rects, rest, bounds, stub=stub)
            if not found:
                continue
            route = simplify(found)
            # only this arrow changed: its crossings and bends against the rest, before and after
            score = {"crossings": best["crossings"] - crossings_with(r, rest) + crossings_with(route, rest), "bends": best["bends"] - bends_of(r) + bends_of(route)}
            # strictly better in (crossings, bends); or it gets the arrow off a box it ran along or through, with no more crossings (the
            # bends may grow: a figure that draws an arrow through a box is wrong)
            ok = (
                score["crossings"] < best["crossings"]
                or (score["crossings"] == best["crossings"] and score["bends"] < best["bends"])
                or (on_box and not touches(i, route) and score["crossings"] <= best["crossings"])
            )
            if not ok:
                continue
            trial = dict(routes)
            trial[i] = route
            # and no more crossings of another arrow's head (they read as joins), no more crossings among the arrows of an AND
            heads2, and2 = head_crossings(list(trial.values())), and_cross(trial)
            if heads2 <= head_cross and and2 <= and_now:
                detours[i] = route
                routes = trial
                best = score
                head_cross, and_now = heads2, and2

    # ADR 0016 D12 (only when asked, after the candidate is chosen; D13 for a direct arrow, below): a long arrow into a grouped head
    # (an AND) whose run through the layers lies along another arrow's run moves its way points aside. Taken only when that leaves no
    # more arrows beside it (any head), makes no more crossings or bends, pierces no box and stays inside the band.
    if aside and group_of:
        heads2s: set[str] = set()
        for i, e in enumerate(lay["edges"]):
            if not e.get("self") and group_of(i) is not None:
                heads2s.add(e["to"])

        def segs(pts: list[dict]) -> list[dict]:
            return [{"p": pts[k], "q": pts[k + 1]} for k in range(len(pts) - 1)]

        def beside(r: dict[int, list[dict]], i: int) -> dict:
            """The arrows whose runs lie along arrow `i`'s: all of them, and those into the
            same head as `i`."""
            mine = segs(r[i])
            all_n, head_n = 0, 0
            for j, o in r.items():
                if j == i or not any(runs_together(x, y) for y in segs(o) for x in mine):
                    continue
                all_n += 1
                if edge_at(j)["to"] == edge_at(i)["to"]:
                    head_n += 1
            return {"all": all_n, "head": head_n}

        def pierces(pts: list[dict], i: int) -> bool:
            e = edge_at(i)
            for seg in segs(pts):
                p, q = seg["p"], seg["q"]
                for node_id, n in lay["nodes"].items():
                    if node_id == e["from"] or node_id == e["to"]:
                        continue
                    if max(p["x"], q["x"]) > n["x"] + 1 and min(p["x"], q["x"]) < n["x"] + n["w"] - 1 and max(p["y"], q["y"]) > n["y"] + 1 and min(p["y"], q["y"]) < n["y"] + n["h"] - 1:
                        return True
            return False

        def inside(pts: list[dict]) -> bool:
            return all(0.5 <= p["y"] <= lay["h"] - 0.5 for p in pts)

        # ADR 0016 D13: a direct arrow's first run lies along the last run of another arrow into the same head (the other turned
        # first): its turn moves to just before or after that arrow's last turn, so the two runs do not overlap along the layers.
        def last_turn_of(r: dict[int, list[dict]], j: int) -> float | None:
            q = r[j]
            return q[-3]["x"] if len(q) >= 4 else None

        for i in list(routes.keys()):
            e = edge_at(i)
            if e.get("self") or e.get("outer") or e["to"] not in heads2s:
                continue
            now = beside(routes, i)
            if not now["head"]:
                continue
            tries: list[Callable[[], None]] = []
            if len(e["points"]) > 2:
                for dz in (8, -8, 16, -16):
                    tries.append(lambda dz=dz: shift_of.update({i: dz}))
            else:
                lo = min(layer_of(e["from"]), layer_of(e["to"]))
                gl = layer_right[lo]
                gr = layer_left.get(lo + 1, gl + 2 * stub)
                for j, o in routes.items():
                    if j == i or edge_at(j)["to"] != e["to"] or not any(runs_together(x, y) for y in segs(o) for x in segs(routes[i])):
                        continue
                    last_turn_x = last_turn_of(routes, j)
                    if last_turn_x is None:
                        continue
                    # the last run keeps room for the arrowhead, on the head's side of the gap (the right for a forward arrow, the left for a return)
                    for x in (last_turn_x - lane, last_turn_x + lane, last_turn_x - 6, last_turn_x + 6):
                        ok_range = (gl + 4 < x < gr - 22) if forward(i) else (gl + 22 < x < gr - 4)
                        if ok_range:
                            tries.append(lambda x=x: turn_at.update({i: x}))
            for set_fn in tries:
                set_fn()
                trial = build()
                s = score_of(list(trial.values()))
                t = beside(trial, i)
                if t["head"] < now["head"] and t["all"] <= now["all"] and s["crossings"] <= best["crossings"] and s["bends"] <= best["bends"] and inside(trial[i]) and not pierces(trial[i], i):
                    routes = trial
                    best = s
                    break
                shift_of.pop(i, None)
                turn_at.pop(i, None)

    return {i: [place(p) for p in pts] for i, pts in routes.items()}


def _better(a: dict, b: dict) -> bool:
    """lib/layered-route.ts:606 better(): (crossings, bends) in lexicographic order, strictly
    better only."""
    return a["crossings"] < b["crossings"] or (a["crossings"] == b["crossings"] and a["bends"] < b["bends"])


def _piercings(a: dict, place: Callable[[dict], dict]) -> int:
    """lib/layered-route.ts:487-502 piercings(): how many arrows run through the inside of a
    box that is not one of their two ends (the boxes and routes are in the placed figure)."""
    rects: dict[str, dict] = {}
    for node_id, n in a["lay"]["nodes"].items():
        p, q = place({"x": n["x"], "y": n["y"]}), place({"x": n["x"] + n["w"], "y": n["y"] + n["h"]})
        rects[node_id] = {"x0": min(p["x"], q["x"]) + 1, "x1": max(p["x"], q["x"]) - 1, "y0": min(p["y"], q["y"]) + 1, "y1": max(p["y"], q["y"]) - 1}
    count = 0
    for i, pts in a["routes"].items():
        e = a["lay"]["edges"][i]
        for node_id, r in rects.items():
            if node_id == e["from"] or node_id == e["to"]:
                continue
            for k in range(1, len(pts)):
                p, q = pts[k - 1], pts[k]
                if min(p["x"], q["x"]) < r["x1"] and max(p["x"], q["x"]) > r["x0"] and min(p["y"], q["y"]) < r["y1"] and max(p["y"], q["y"]) > r["y0"]:
                    count += 1
                    break
    return count


def layered_attempt(nodes: list[dict], edges: list[dict], layout_opts: dict, o: dict) -> dict:
    """lib/layered-route.ts:512-603 layeredAttempt(): one layered layout with its routes,
    score, size and undrawable groups — the unit the callers (causeTree, stateDiagram,
    classDiagram, the semantic networks; none wired to this port yet, see BANDS.md's Tier 3
    note) build a figure from. Two candidates are laid out: the plain one (centre each layer,
    relax toward the neighbours) and a straightened one (Brandes-Köpf coordinates, crossing-
    minimal order, optionally tightened layers). The straightened one is dropped when it
    leaves an AND undrawable that the plain one drew, runs an arrow through a box the plain
    one did not, or does not fit a width the plain one fits. Of what is left it replaces the
    plain one only if (crossings, bends) is strictly better in the lexicographic order, or if
    the plain one does not fit the width and it does. Nothing else moves a figure.

    `o` (AttemptOpts, see the TS interface for full field docs): portStep/groupOf/transpose/
    maxAcross/place(required)/round/looseOf/straighten/tighten/space/detour/apart/aside/
    returns.

    `optsOf` (Node's `WeakMap<Attempt, {...}>`, keyed by object identity) is an `id(attempt)`-
    keyed dict here — safe because every `Attempt` dict this function builds (`plain`/`cand`/
    `far`/`c`/`made`/etc.) is held by a local variable for the whole of its lookup lifetime
    inside this one call, so CPython can never recycle its `id()` in between (the same
    invariant `treemap.py`'s `id(n)`-keyed `weight` dict relies on).
    """
    lane_heads = False
    opts_of: dict[int, dict] = {}
    o_group_of: Callable[[int], int | None] | None = o.get("groupOf")
    o_place: Callable[[dict], Callable[[dict], dict]] = o["place"]
    o_loose_of = o.get("looseOf")
    space = o.get("space", 1)

    def build(opts: dict, lane_share: bool = False, aside_flag: bool = False, near: str = "far") -> dict:
        if o.get("returns"):
            outer_spec = {"which": o["returns"], "gap": stub_of(space), "step": lane_step_of(space)}
            if near != "far":
                outer_spec["side"] = near
            full_opts = {**opts, "outer": outer_spec}
        else:
            full_opts = opts
        lay = layout_with_lanes(nodes, edges, full_opts, 0, space)
        size = {"w": lay["h"] if o.get("transpose") else lay["w"], "h": lay["w"] if o.get("transpose") else lay["h"]}
        group_of_wrapped = (lambda i, _g=o_group_of: _g(lay["edges"][i]["index"])) if o_group_of else None
        # the search for a way around the boxes only in the straightened candidate (it competes with the plain one on bends); a lone port is straightened in both
        detour_flag = o.get("detour") is True and opts.get("coord") == "bk"
        lone_ports = o.get("detour") is True
        routes = route_layered(
            lay, o_place(size), o.get("portStep", 14), group_of_wrapped, o.get("round"),
            o.get("straighten") is not False, lane_share, aside_flag, detour_flag, lone_ports, space, lane_heads,
        )
        made = {
            "lay": lay,
            "routes": routes,
            "score": score_of(list(routes.values())),
            "size": size,
            "fits": o.get("maxAcross") is None or size["w"] <= o["maxAcross"],
            "loose": o_loose_of(routes, lay) if o_loose_of else [],
        }
        opts_of[id(made)] = {"opts": opts, "laneShare": lane_share, "near": near}
        return made

    # ADR 0016 D11: arrows into a grouped head that run side by side. A candidate that shares the gap's lanes between the long and the
    # direct arrows replaces the figure only when it has strictly fewer of them and is no worse in (crossings, bends), loose groups,
    # piercings and width: a figure with none is never touched.
    def parallels(a: dict) -> int:
        group_of = o_group_of
        assert group_of is not None
        heads: set[str] = set()
        for e in a["lay"]["edges"]:
            if not e.get("self") and group_of(e["index"]) is not None:
                heads.add(e["to"])
        segs = []
        for i, pts in a["routes"].items():
            e = a["lay"]["edges"][i]
            if e["to"] in heads:
                segs.append({"to": e["to"], "s": [{"p": pts[m], "q": pts[m + 1]} for m in range(len(pts) - 1)]})
        n = 0
        for x in range(len(segs)):
            sx = segs[x]
            for sy in segs[x + 1 :]:
                if sx["to"] == sy["to"] and any(runs_together(p, q) for p in sx["s"] for q in sy["s"]):
                    n += 1
        return n

    def worse(a: dict, b: dict) -> bool:
        if len(b["loose"]) > len(a["loose"]):
            return True
        if a["fits"] and not b["fits"]:
            return True
        if _better(a["score"], b["score"]):
            return True
        return _piercings(b, o_place(b["size"])) > _piercings(a, o_place(a["size"]))

    # the AND-bound arrows that cross each other
    def and_crossings(a: dict) -> int:
        group_of = o_group_of
        assert group_of is not None
        heads: set[str] = set()
        for e in a["lay"]["edges"]:
            if not e.get("self") and group_of(e["index"]) is not None:
                heads.add(e["to"])
        return crossings_of([pts for i, pts in a["routes"].items() if a["lay"]["edges"][i]["to"] in heads])

    # ADR 0016 D12: what is chosen then gets its remaining side-by-side runs moved aside, once; kept only when nothing else gets worse
    def aside_pass(a: dict) -> dict:
        before = parallels(a)
        if not before:
            return a
        conf = opts_of[id(a)]
        b = build(conf["opts"], conf["laneShare"], True, conf["near"])
        if parallels(b) >= before or worse(a, b) or and_crossings(b) > and_crossings(a):
            return a
        b["asided"] = True
        return b

    def sharing(a: dict) -> dict:
        if not o_group_of:
            return a
        before = parallels(a)
        if not before:
            return a
        conf = opts_of[id(a)]
        b = build(conf["opts"], True, False, conf["near"])
        chosen = a if (parallels(b) >= before or worse(a, b)) else b
        return chosen if o.get("aside") is False else aside_pass(chosen)

    # ADR 0016 D14: what is chosen gets the runs of arrows with no end in common that lie along each other moved apart, once; kept only
    # when nothing else gets worse
    def apart_of(a: dict) -> dict:
        if not o.get("apart"):
            return a
        place = o_place(a["size"])
        rects: dict[str, dict] = {}
        for node_id, n in a["lay"]["nodes"].items():
            p, q = place({"x": n["x"], "y": n["y"]}), place({"x": n["x"] + n["w"], "y": n["y"] + n["h"]})
            rects[node_id] = {"x0": min(p["x"], q["x"]) + 1, "x1": max(p["x"], q["x"]) - 1, "y0": min(p["y"], q["y"]) + 1, "y1": max(p["y"], q["y"]) - 1}
        move_edges = {i: {"from": e["from"], "to": e["to"], "self": e.get("self"), "outer": e.get("outer")} for i, e in enumerate(a["lay"]["edges"])}
        routes = move_apart(a["routes"], move_edges, rects)
        if all(routes[i] is a["routes"][i] for i in routes):
            return a
        b = {**a, "routes": routes, "score": score_of(list(routes.values())), "loose": o_loose_of(routes, a["lay"]) if o_loose_of else []}
        opts_of[id(b)] = opts_of[id(a)]
        if worse(a, b) or (o_group_of is not None and (and_crossings(b) > and_crossings(a) or parallels(b) > parallels(a))):
            return a
        # the search of the orders is entered on the first figure's crossings (toc.ts): a move that takes the last crossing away would skip it where it ran
        if a["score"]["crossings"] > 0 and b["score"]["crossings"] == 0:
            return a
        # an AND crossing it took away is judged like D12/D13's: toc.ts decides whether to search the orders on the figure without these moves
        if o_group_of is not None and and_crossings(b) < and_crossings(a):
            b["asided"] = True
        return b

    def pick0(near: str) -> dict:
        plain = build(layout_opts, False, False, near)
        if o.get("straighten") is False or not any(e["from"] != e["to"] for e in edges):
            return sharing(plain)
        cand_opts = {**layout_opts, "coord": "bk", "transpose": True}
        if o.get("tighten"):
            cand_opts["tighten"] = True
        cand = build(cand_opts, False, False, near)
        if len(cand["loose"]) > len(plain["loose"]):
            return sharing(plain)
        if _piercings(cand, o_place(cand["size"])) > _piercings(plain, o_place(plain["size"])):
            return sharing(plain)
        if not plain["fits"]:
            return sharing(cand if (cand["fits"] or (cand["size"]["w"] < plain["size"]["w"] and _better(cand["score"], plain["score"]))) else plain)
        if not cand["fits"]:
            return sharing(plain)
        return sharing(cand if _better(cand["score"], plain["score"]) else plain)

    def pick(near: str) -> dict:
        return apart_of(pick0(near))

    # a return's lane goes to the side its ends are nearer to, only when that is strictly better in (crossings, bends) and nothing else
    # gets worse (the far side is the way it always was)
    far = pick("far")
    if not o.get("returns") or o.get("straighten") is False or not any(e.get("outer") for e in far["lay"]["edges"]):
        return far
    # not bigger than the far one: the width and the height are the caller's budget (a taller figure may not fit the canvas), and lanes
    # on both sides take more room than on one
    result = far
    for side in ("near", "low"):
        c = pick(side)
        if any(e.get("outer") for e in c["lay"]["edges"]) and c["lay"]["w"] <= far["lay"]["w"] + 0.01 and c["lay"]["h"] <= far["lay"]["h"] + 0.01 and not worse(result, c) and _better(c["score"], result["score"]):
            result = c
    # a return that enters its head's face instead of its right side, only when that takes crossings away (fewer bends alone moves
    # nothing) and nothing else gets worse
    lane_heads = True
    c = pick(opts_of[id(result)]["near"])
    lane_heads = False
    if any(e.get("outer") for e in c["lay"]["edges"]) and c["lay"]["w"] <= result["lay"]["w"] + 0.01 and c["lay"]["h"] <= result["lay"]["h"] + 0.01 and not worse(result, c) and c["score"]["crossings"] < result["score"]["crossings"]:
        return c
    return result
