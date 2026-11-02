"""1:1 port of lib/states-words.ts: the words a state diagram and a flowchart (a state
diagram with decisions, ADR 0041) use for the same things in messages.

Golden master: lib/states-words.ts (Node.js, svg-diagram).
"""

from __future__ import annotations

_STATE = {"who": "stateDiagram()", "diagram": "a state diagram", "node": "state", "edge": "transition", "prefix": "states"}
_FLOW = {"who": "flowchart()", "diagram": "a flowchart", "node": "node", "edge": "arrow", "prefix": "flowchart"}


def states_words(flavor: str | None) -> dict:
    return _FLOW if flavor == "flowchart" else _STATE
