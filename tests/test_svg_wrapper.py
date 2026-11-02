"""Static golden tests for emit_svg() against captured Node emitSvg() output.

emitSvgWith() (the actual Node function that builds the <svg> wrapper) is not
exported, and the exported emitSvg() needs a full LaidOutDiagram — so instead
of a live subprocess comparison (like test_golden_box.py), these fixtures
were captured ONCE from a real `node --input-type=module -e "import
{emitSvg} ..."` call and committed. See golden/fixtures/*.json for the
exact command and the plan's notes on why this function can't be import-golden-tested live.
"""

import json
from pathlib import Path

import pytest

from svg_diagram.emit import emit_svg

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "golden" / "fixtures"


@pytest.mark.parametrize("fixture_name", ["svg_wrapper_empty.json", "svg_wrapper_box_connect.json"])
def test_emit_svg_matches_captured_node_output(fixture_name):
    fixture = json.loads((FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))
    has_arrow = any(c.get("arrow", "end") != "none" for c in fixture["input"]["connects"])
    result = emit_svg(
        width=fixture["input"]["width"],
        height=fixture["input"]["height"],
        body=fixture.get("body", ""),
        connect_svg=fixture.get("connectSvg", ""),
        has_arrow=has_arrow,
    )
    assert result == fixture["svg"]
