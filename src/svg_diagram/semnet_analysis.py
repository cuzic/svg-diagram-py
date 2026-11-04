"""1:1 port of lib/semnet-analysis.ts: analyze_critical_path() (pert()'s CPM analysis) and
analyze_causal_loops() (causalLoop()'s directed-simple-cycle enumeration).

Pure: no layout, fonts or SVG.

Golden master: lib/semnet-analysis.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math
from typing import NoReturn


def _semnet_error(who: str, message: str) -> NoReturn:
    raise ValueError(f"{who}(): {message}")


def analyze_critical_path(input_: list[dict]) -> dict:
    """lib/semnet-analysis.ts:9-55 analyzeCriticalPath(). `input_`: [{id, label, duration,
    predecessors?}, ...]. Returns {tasks, duration, criticalPath, criticalEdges}."""
    if not input_:
        _semnet_error("pert", "needs at least one task")
    order: dict[str, int] = {}
    by_id: dict[str, dict] = {}
    for i, t in enumerate(input_):
        if not isinstance(t.get("id"), str) or not t["id"].strip():
            _semnet_error("pert", f"tasks[{i}].id must be a non-empty string")
        if t["id"] in by_id:
            _semnet_error("pert", f'duplicate task id "{t["id"]}"')
        if not isinstance(t.get("label"), str) or not t["label"].strip():
            _semnet_error("pert", f"task \"{t['id']}\"'s label must be a non-empty string")
        duration = t.get("duration")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not math.isfinite(duration) or duration < 0:
            _semnet_error("pert", f"task \"{t['id']}\"'s duration must be a finite number >= 0")
        order[t["id"]] = i
        by_id[t["id"]] = t

    pred: dict[str, list[str]] = {}
    succ: dict[str, list[str]] = {t["id"]: [] for t in input_}
    for t in input_:
        ps = list(t.get("predecessors") or [])
        if len(set(ps)) != len(ps):
            _semnet_error("pert", f'task "{t["id"]}" repeats a predecessor')
        for p in ps:
            if p not in by_id:
                _semnet_error("pert", f'task "{t["id"]}" names unknown predecessor "{p}"')
            if p == t["id"]:
                _semnet_error("pert", f'cycle detected: {t["id"]} -> {t["id"]}')
            succ[p].append(t["id"])
        pred[t["id"]] = ps

    indegree = {t["id"]: len(pred[t["id"]]) for t in input_}
    ready = [t["id"] for t in input_ if not indegree[t["id"]]]
    topo: list[str] = []
    while ready:
        ready.sort(key=lambda a: order[a])
        tid = ready.pop(0)
        topo.append(tid)
        for n in succ[tid]:
            indegree[n] -= 1
            if not indegree[n]:
                ready.append(n)
    if len(topo) != len(input_):
        cyclic = [t["id"] for t in input_ if indegree[t["id"]] > 0]
        _semnet_error("pert", f"cycle detected among tasks: {', '.join(cyclic)}")

    es: dict[str, float] = {}
    ef: dict[str, float] = {}
    for tid in topo:
        start = max([0.0, *(ef[p] for p in pred[tid])])
        es[tid] = start
        ef[tid] = start + by_id[tid]["duration"]
    duration = max(ef[tid] for tid in topo)
    lf: dict[str, float] = {}
    ls: dict[str, float] = {}
    for tid in reversed(topo):
        finish = min((ls[s] for s in succ[tid]), default=duration) if succ[tid] else duration
        lf[tid] = finish
        ls[tid] = finish - by_id[tid]["duration"]

    tasks: list[dict] = []
    for t in input_:
        tid = t["id"]
        slack = ls[tid] - es[tid]
        tasks.append({**t, "predecessors": list(pred[tid]), "es": es[tid], "ef": ef[tid], "ls": ls[tid], "lf": lf[tid], "slack": slack, "critical": abs(slack) < 1e-9})

    by_task_id = {t["id"]: t for t in tasks}
    critical_edges: list[dict] = []
    for t in tasks:
        for p in t["predecessors"]:
            if by_task_id[p]["critical"] and t["critical"] and abs(ef[p] - es[t["id"]]) < 1e-9:
                critical_edges.append({"from": p, "to": t["id"]})

    # One deterministic representative path; criticalEdges still records parallel/tied paths.
    critical_path: list[str] = []
    current = next((t["id"] for t in tasks if t["critical"] and t["es"] == 0), None)
    while current is not None:
        critical_path.append(current)
        candidates = sorted((e for e in critical_edges if e["from"] == current), key=lambda e: order[e["to"]])
        current = candidates[0]["to"] if candidates else None
    return {"tasks": tasks, "duration": duration, "criticalPath": critical_path, "criticalEdges": critical_edges}


def analyze_causal_loops(nodes: list[str], links: list[dict]) -> list[dict]:
    """lib/semnet-analysis.ts:63-85 analyzeCausalLoops(): all directed simple cycles, once
    each, ordered by node input order. A direct self-loop (from==to) counts too (a
    single-node "cycle"); causalLoop()'s ring layout filters those out itself."""
    index: dict[str, int] = {}
    for i, node_id in enumerate(nodes):
        if not node_id or node_id in index:
            _semnet_error("causalLoop", f'node ids must be non-empty and unique (got "{node_id}")')
        index[node_id] = i
    out: dict[str, list[dict]] = {node_id: [] for node_id in nodes}
    for i, e in enumerate(links):
        if e["from"] not in index or e["to"] not in index:
            _semnet_error("causalLoop", f"link {e['from']} -> {e['to']} names unknown node")
        if e["polarity"] not in ("+", "-", "same", "opposite"):
            _semnet_error("causalLoop", f"link {e['from']} -> {e['to']} has invalid polarity \"{e['polarity']}\"")
        out[e["from"]].append({"to": e["to"], "edge": i})

    cycles: list[dict] = []
    for si, start in enumerate(nodes):
        path = [start]
        edges: list[int] = []
        seen = {start}

        def visit(at: str) -> None:
            for e in out[at]:
                if e["to"] == start:
                    link_indexes = [*edges, e["edge"]]
                    negative_links = sum(1 for idx in link_indexes if links[idx]["polarity"] in ("-", "opposite"))
                    cycles.append({"nodes": list(path), "linkIndexes": link_indexes, "negativeLinks": negative_links, "kind": "B" if negative_links % 2 else "R"})
                elif e["to"] not in seen and index[e["to"]] >= si:
                    seen.add(e["to"])
                    path.append(e["to"])
                    edges.append(e["edge"])
                    visit(e["to"])
                    edges.pop()
                    path.pop()
                    seen.discard(e["to"])

        visit(start)
    return cycles
