#!/usr/bin/env python3
"""Measures how much of svg_diagram's own logic is actually exercised by the test suite, and
ratchets it so a regression never slips in silently.

Line coverage from coverage.py (`pytest --cov=svg_diagram --cov-report=json`), kept per-file
(not just a single total) so that adding tests for one file can never silently mask a drop in
another — same reasoning as type_safety_report.py's per-file error counts.

Coverage isn't a proxy for test quality (a line can be "covered" by an assertion-free call),
but *uncovered* lines are the honest part of the signal: a branch nothing exercises is a branch
nothing protects against regressing. Treat low-coverage files as a worklist, not every missing
line as something to chase — golden-master comparison files (tests/ already covers these via
node_golden) and defensive-only branches are lower priority than untested real logic.

Not a pytest test: running pytest with --cov instrumentation takes ~5x longer than a plain run
(measured: 115s vs 22s for this project), so this stays a separate, by-hand/CI step.

Usage:
    uv run python scripts/coverage_report.py            # report + fail on regression
    uv run python scripts/coverage_report.py --update   # also write the new baseline
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = Path(__file__).resolve().parent / "coverage_baseline.json"


def measure() -> dict:
    print("running pytest --cov=svg_diagram...", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        json_path = Path(tmp) / "coverage.json"
        proc = subprocess.run(
            ["uv", "run", "pytest", "--cov=svg_diagram", "--cov-report", f"json:{json_path}", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if not json_path.exists():
            print(proc.stdout, file=sys.stderr)
            print(proc.stderr, file=sys.stderr)
            raise SystemExit(f"pytest --cov did not produce a coverage report (exit {proc.returncode})")
        data = json.loads(json_path.read_text())

    by_file: dict[str, dict] = {}
    for f, info in data["files"].items():
        rel = str(Path(f).resolve().relative_to(ROOT))
        s = info["summary"]
        by_file[rel] = {"num_statements": s["num_statements"], "missing_lines": s["missing_lines"], "percent_covered": s["percent_covered"]}

    totals = data["totals"]
    return {
        "percent_covered": totals["percent_covered"],
        "missing_lines_total": totals["missing_lines"],
        "by_file": dict(sorted(by_file.items())),
    }


def print_report(current: dict, baseline: dict | None) -> None:
    print()
    print(f"line coverage: {current['percent_covered']:.1f}%  (missing {current['missing_lines_total']} lines across {len(current['by_file'])} files)")
    if baseline is not None:
        delta = current["percent_covered"] - baseline["percent_covered"]
        sign = "+" if delta >= 0 else ""
        print(f"  vs baseline {baseline['percent_covered']:.1f}%  ({sign}{delta:.1f}%)")
    print()


def find_regressions(current: dict, baseline: dict) -> list[str]:
    problems = []
    if current["percent_covered"] < baseline["percent_covered"]:
        problems.append(f"overall coverage dropped: {baseline['percent_covered']:.1f}% -> {current['percent_covered']:.1f}%")
    for f, info in current["by_file"].items():
        base_info = baseline["by_file"].get(f)
        base_missing = base_info["missing_lines"] if base_info else 0
        if info["missing_lines"] > base_missing:
            problems.append(f"{f}: missing lines {base_missing} -> {info['missing_lines']}")
    return problems


def print_worklist(current: dict, n: int = 15) -> None:
    worst = sorted(current["by_file"].items(), key=lambda kv: kv[1]["missing_lines"], reverse=True)[:n]
    print(f"worst-covered files (top {n} by missing-line count):")
    for f, info in worst:
        print(f"  {info['percent_covered']:5.1f}%  missing={info['missing_lines']:<4}  {f}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="write the measured result as the new baseline")
    parser.add_argument("--worklist", action="store_true", help="print the worst-covered files and exit")
    args = parser.parse_args()

    current = measure()

    if args.worklist:
        print_report(current, None)
        print_worklist(current)
        return 0

    if args.update or not BASELINE_PATH.exists():
        BASELINE_PATH.write_text(json.dumps(current, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        print_report(current, None)
        print(f"baseline written to {BASELINE_PATH.relative_to(ROOT)}")
        return 0

    baseline = json.loads(BASELINE_PATH.read_text())
    print_report(current, baseline)

    problems = find_regressions(current, baseline)
    if problems:
        print("REGRESSIONS:")
        for p in problems:
            print(f"  - {p}")
        print("\nIf intentional (e.g. mid-refactor), rerun with --update once the dust settles.")
        return 1

    if current["percent_covered"] > baseline["percent_covered"]:
        print("No regressions, and it looks better than the baseline — rerun with --update to lock it in.")
    else:
        print("No regressions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
