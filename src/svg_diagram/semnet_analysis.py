"""Scoped port of lib/semnet-analysis.ts — only analyze_critical_path() (pert()'s CPM
analysis), which pert.py needs. analyzeCausalLoops() (causalLoop()'s cycle detection) is NOT
ported: causalLoop() itself is out of this port's scope (it also needs lib/semnet-ring.ts
and lib/semnet-interventions.ts, not yet ported).

Pure: no layout, fonts or SVG.

Golden master: lib/semnet-analysis.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

import math


def _semnet_error(who: str, message: str) -> None:
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
