"""Golden tests for pyramid geometry/rendering, against a fixture captured from the real
Node.js pipeline (layoutPyramid()/renderPyramid() aren't exported — see
golden/fixtures/pyramid_example.json for how this was captured and why it's a static
fixture rather than a live subprocess call, same technique as test_svg_wrapper.py)."""

import json
from pathlib import Path

from svg_diagram.figures import pyramid_layer_geometry, render_pyramid

FIXTURE = json.loads((Path(__file__).resolve().parents[1] / "golden" / "fixtures" / "pyramid_example.json").read_text(encoding="utf-8"))


def test_pyramid_layer_geometry_matches_captured_node_layout():
    band = FIXTURE["laidOutBand"]
    n = len(band["layers"])
    for i, expected in enumerate(band["layers"]):
        geom = pyramid_layer_geometry(n=n, i=i, base_width=band["w"], apex_ratio=0.3, layer_height=76, cx=470, stack_bottom_y=band["y"] + band["h"])
        assert [list(p) for p in geom["points"]] == expected["points"]
        assert geom["opacity"] == expected["opacity"]


def test_render_pyramid_matches_captured_node_output():
    layers = FIXTURE["laidOutBand"]["layers"]
    result = render_pyramid(layers, day=FIXTURE["laidOutBand"]["day"])
    assert result == FIXTURE["renderedBody"]
