"""Golden-master tests for run_color_of() against Node's runColorOf()."""

import pytest

from svg_diagram.tokens import run_color_of

TONE_NAMES = ["plain", "accent", "danger", "muted", "new", "changed", "removed", "solid", "solid-danger"]


@pytest.mark.parametrize("box_tone", [None, *TONE_NAMES])
def test_run_color_of_with_no_run_override_matches_node(node_golden, box_tone):
    # runTone is deliberately OMITTED (not set to JSON null): Node's runColorOf checks `runTone ===
    # undefined`, and JSON has no way to express `undefined` — only an absent key round-trips as that.
    node_result = node_golden.call({"kind": "runColorOf", "boxTone": box_tone})
    assert run_color_of(None, box_tone, day=1) == node_result


@pytest.mark.parametrize("run_tone", ["accent", "danger", "muted"])
def test_run_color_of_with_run_override_matches_node(node_golden, run_tone):
    # a run's own tone wins even on a solid box
    node_result = node_golden.call({"kind": "runColorOf", "runTone": run_tone, "boxTone": "solid"})
    assert run_color_of(run_tone, "solid", day=1) == node_result
