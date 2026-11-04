#!/usr/bin/env python3
"""Measures how much of svg_diagram is actually protected by types, not just annotated with
them, and ratchets it so a regression never slips in silently.

Two numbers, from pyright itself (no custom type-checking logic here):

- **Type completeness** (`pyright --verifytypes svg_diagram`): the share of the package's
  symbols whose type is *known* rather than `Unknown`/implicit `Any`. This is the "how much
  of the codebase could even be checked in the first place" number — a file full of bare
  `dict`/`Any` can show zero pyright *errors* while being completely unprotected; this score
  is what catches that.
- **Error count per file** (`pyright`, whole project): the usual "did we break something"
  number pyright already reports, kept per-file (not just a single total) so that fixing one
  file's errors can never silently mask a new regression appearing in a different file.

Not a pytest test: a full `pyright` pass over this project takes ~30s (`--verifytypes` alone
is ~5s), which is too slow to run on every `uv run pytest`. Run this by hand, or wire it into
CI as its own step, same as `ruff`/`pyright` already are.

Usage:
    uv run python scripts/type_safety_report.py            # report + fail on regression
    uv run python scripts/type_safety_report.py --update   # also write the new baseline
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = Path(__file__).resolve().parent / "type_safety_baseline.json"


def _run_pyright(*args: str) -> dict:
    proc = subprocess.run(["uv", "run", "pyright", "--outputjson", *args], cwd=ROOT, capture_output=True, text=True)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"pyright --outputjson {' '.join(args)} did not return JSON (exit {proc.returncode})")


def measure() -> dict:
    print("running pyright over the whole project...", file=sys.stderr)
    errors = _run_pyright()
    by_file: dict[str, int] = {}
    for d in errors["generalDiagnostics"]:
        f = str(Path(d["file"]).resolve().relative_to(ROOT))
        by_file[f] = by_file.get(f, 0) + 1

    print("running pyright --verifytypes svg_diagram...", file=sys.stderr)
    vt = _run_pyright("--verifytypes", "svg_diagram")
    tc = vt["typeCompleteness"]
    counts = tc["exportedSymbolCounts"]

    return {
        "error_count_total": errors["summary"]["errorCount"],
        "error_count_by_file": dict(sorted(by_file.items())),
        "completeness_score": tc["completenessScore"],
        "known_types": counts["withKnownType"],
        "ambiguous_types": counts["withAmbiguousType"],
        "unknown_types": counts["withUnknownType"],
    }


def print_report(current: dict, baseline: dict | None) -> None:
    print()
    print(f"type completeness: {current['completeness_score']:.1%}  (known={current['known_types']}, ambiguous={current['ambiguous_types']}, unknown={current['unknown_types']})")
    if baseline is not None:
        delta = current["completeness_score"] - baseline["completeness_score"]
        sign = "+" if delta >= 0 else ""
        print(f"  vs baseline {baseline['completeness_score']:.1%}  ({sign}{delta:.1%})")
    print(f"pyright errors: {current['error_count_total']} across {len(current['error_count_by_file'])} files")
    if baseline is not None:
        delta_n = current["error_count_total"] - baseline["error_count_total"]
        sign = "+" if delta_n >= 0 else ""
        print(f"  vs baseline {baseline['error_count_total']}  ({sign}{delta_n})")
    print()


def find_regressions(current: dict, baseline: dict) -> list[str]:
    problems = []
    if current["completeness_score"] < baseline["completeness_score"]:
        problems.append(f"type completeness dropped: {baseline['completeness_score']:.1%} -> {current['completeness_score']:.1%}")
    for f, n in current["error_count_by_file"].items():
        base_n = baseline["error_count_by_file"].get(f, 0)
        if n > base_n:
            problems.append(f"{f}: pyright errors {base_n} -> {n}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true", help="write the measured result as the new baseline")
    args = parser.parse_args()

    current = measure()

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

    improved = current["completeness_score"] > baseline["completeness_score"] or current["error_count_total"] < baseline["error_count_total"]
    if improved:
        print("No regressions, and it looks better than the baseline — rerun with --update to lock it in.")
    else:
        print("No regressions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
