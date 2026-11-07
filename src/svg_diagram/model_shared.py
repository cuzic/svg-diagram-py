"""Tiny helpers shared by every Diagram band-method mixin (model_*.py) — not a port of
anything in lib/, just this port's own plumbing. Lives outside model.py so the mixins can
import it without a circular import back to model.py (which imports the mixins).
"""

from __future__ import annotations

from typing import Literal, Protocol

Tone = Literal["plain", "accent", "danger", "muted", "new", "changed", "removed", "solid", "solid-danger"]
ArrowStyle = Literal["start", "end", "both", "none"]
LineStyle = Literal["solid", "dashed", "dotted"]


class Renderable(Protocol):
    """What every element of Diagram._elements has in common: each one's own dataclass (in
    whichever model_*.py owns that domain) knows how to turn itself into SVG — see the
    model.py module docstring for why this replaced a central dispatch function.

    `bottom()` is this port's own addition (not a port of anything in lib/, same as the
    rest of model.py): the lowest y-coordinate the element's content reaches, used by
    `Diagram(width, height="auto")` to size the canvas to its content. For a band whose
    own layout_X() computes a height from content, `bottom()` repeats that same call
    (cheap, and keeps render() and bottom() independent — no caching between them, same
    as render() itself recomputing layout fresh on every call)."""

    def render(self) -> str: ...
    def bottom(self) -> float: ...


def _opts(*pairs: tuple[str, object]) -> dict:
    """The kwarg-to-opts-dict collection every chart-family Diagram method repeats at its
    tail (keep only the kwargs the caller actually set): opts = {k: v for (k, v) in pairs if
    v is not None}."""
    return {k: v for k, v in pairs if v is not None}
