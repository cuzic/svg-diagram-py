"""Diagram band methods for the "process diagrams" domain — RCA (bowtie/faultTree), UML
classes, BPMN, state/flow diagrams and cause trees. Each is its own standalone band type
(not part of the "chart" family), with its own layout_X()/render_X() pair. Mixed into
`Diagram` by model.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from .approx_width import approx_width_of
from .bowtie import bowtie_band, layout_bowtie, render_bowtie
from .bpmn import bpmn_band, layout_bpmn, render_bpmn
from .classes import classes_band, layout_classes_band, render_classes
from .fta import fta_band, layout_fta, render_fta
from .model_shared import Renderable
from .states import flowchart_band, layout_states_band, render_states, states_band
from .toc import cause_band, layout_cause_band, render_cause
from .tokens import ROLES


@dataclass
class _Bowtie:
    """bowtie() is a standalone band type ("bowtie"), not part of the "chart" family —
    its own layout_bowtie()/render_bowtie() pair (lib/bowtie.ts/lib/emit-bowtie.ts)."""

    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_bowtie(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return render_bowtie(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_bowtie(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return laid.get("y", self.y) + laid["h"]


@dataclass
class _Fta:
    """faultTree() is a standalone band type ("fta"), not part of the "chart" family —
    its own layout_fta()/render_fta() pair (lib/fta.ts/lib/emit-fta.ts)."""

    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_fta(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return render_fta(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_fta(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return laid.get("y", self.y) + laid["h"]


@dataclass
class _Bpmn:
    """bpmn() is a standalone band type ("bpmn"), not part of the "chart" family —
    its own layout_bpmn()/render_bpmn() pair (lib/bpmn.ts/lib/emit-figures.ts)."""

    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_bpmn(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return render_bpmn(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_bpmn(self.band, self.x, self.y, self.w, approx_width_of, ROLES, "phrase")
        return laid.get("y", self.y) + laid["h"]


@dataclass
class _Classes:
    """classDiagram() is a standalone band type ("classes"), not part of the "chart" family —
    its own layout_classes_band()/render_classes() pair (lib/classes.ts/lib/emit-figures.ts)."""

    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_classes_band(self.band, self.x, self.y, self.w, approx_width_of, ROLES, {"wrap": "phrase", "keepWords": False})
        return render_classes(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_classes_band(self.band, self.x, self.y, self.w, approx_width_of, ROLES, {"wrap": "phrase", "keepWords": False})
        return laid.get("y", self.y) + laid["h"]


@dataclass
class _States:
    """stateDiagram()/flowchart() are a standalone band type ("states"), not part of the
    "chart" family — their own layout_states_band()/render_states() pair
    (lib/states.ts/lib/emit-figures.ts)."""

    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_states_band(self.band, self.x, self.y, self.w, approx_width_of, ROLES, {"wrap": "phrase", "keepWords": False})
        return render_states(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_states_band(self.band, self.x, self.y, self.w, approx_width_of, ROLES, {"wrap": "phrase", "keepWords": False})
        return laid.get("y", self.y) + laid["h"]


@dataclass
class _Cause:
    """causeTree() is a standalone band type ("cause"), not part of the "chart" family — its
    own layout_cause_band()/render_cause() pair (lib/toc.ts/lib/emit-figures.ts)."""

    x: float
    y: float
    w: float
    band: dict
    day: int | str = 1

    def render(self) -> str:
        laid = layout_cause_band(self.band, self.x, self.y, self.w, approx_width_of, ROLES, {"wrap": "phrase", "keepWords": False})
        return render_cause(laid, day=self.day)

    def bottom(self) -> float:
        laid = layout_cause_band(self.band, self.x, self.y, self.w, approx_width_of, ROLES, {"wrap": "phrase", "keepWords": False})
        return laid.get("y", self.y) + laid["h"]


class ProcessMixin:
    _elements: list[Renderable]

    def bowtie(self, input: dict, *, x: float, y: float, width: float, max_node_w: float | str | None = None, id: str | None = None) -> None:
        """lib/dsl/diagrams.ts's bowtie(): a bow-tie diagram — threats on the left, each
        through its preventive barriers, into the top event (under its hazard) in the
        middle; out through the mitigating barriers to the consequences on the right.
        `input`: {hazard?, top, threats: [{label, barriers?}, ...], consequences: [{label,
        barriers?}, ...]}. `max_node_w`: the widest a box grows (default 200, narrowed to
        160/130/110 if the figure does not fit the width); 'auto' does the same; a number is
        never narrowed."""
        band = bowtie_band(input, max_node_w=max_node_w, id=id)
        self._elements.append(_Bowtie(x=x, y=y, w=width, band=band))

    def fault_tree(self, root: dict, *, x: float, y: float, width: float, max_node_w: float | str | None = None, cut_sets: bool | None = None, quant: bool | None = None, quant_period: str | None = None, id: str | None = None) -> None:
        """lib/dsl/diagrams.ts's faultTree(): a fault tree (FTA) — the top event, with a
        gate (and/or/vote/inhibit) and its causes down to basic/undeveloped/house/condition
        events. `root`: {label, kind?, gate?, children?, k?, condition?, p?, state?, id?,
        ref?} recursively. `cut_sets`: mark the events that alone bring the top event about.
        `quant`: work out and write the top event's probability from each event's `p`."""
        band = fta_band(root, max_node_w=max_node_w, cut_sets=cut_sets, quant=quant, quant_period=quant_period, id=id)
        self._elements.append(_Fta(x=x, y=y, w=width, band=band))

    def bpmn(self, lanes: list[dict], nodes: list[dict], flows: list[dict], *, x: float, y: float, width: float, fit: str | None = None, id: str | None = None) -> None:
        """lib/dsl/diagrams.ts's bpmn(): a business flow in lanes, BPMN-style — tasks,
        start/end events and gateways (xor/and/or), joined by sequence flows (solid) and
        message flows (dashed). `lanes`: [{id, label, tone?}]. `nodes`: [{id, lane, label?,
        sub?, kind?, tone?}]. `flows`: [{from, to, label?, line?}]. `fit: 'shrink'`: narrow
        the figure step by step until it fits (default: raise). A task's `icon`/`iconTone`
        are NOT supported (see bpmn.py's module docstring)."""
        band = bpmn_band(lanes, nodes, flows, fit=fit, id=id)
        self._elements.append(_Bpmn(x=x, y=y, w=width, band=band))

    def classes(self, classes: list[dict], relations: list[dict], *, x: float, y: float, width: float, dir: str | None = None, straighten: bool | None = None, id: str | None = None) -> None:
        """lib/dsl/diagrams.ts's classDiagram(): UML classes (name/attributes/methods
        compartments) and the relations between them, placed in layers so a parent sits
        above its children. `classes`: [{id, name?, stereotype?, abstract?, attrs?,
        methods?, tone?}]. `relations`: [{from, to, kind?, label?, fromMult?, toMult?}] —
        `kind`: assoc(default)/arrow/inherit/implement/compose/aggregate/depend. `dir`:
        'down'(default)/'right'/'auto'."""
        band = classes_band(classes, relations, dir=dir, straighten=straighten, id=id)
        self._elements.append(_Classes(x=x, y=y, w=width, band=band))

    def state_diagram(
        self, states: list[dict], transitions: list[dict], *, x: float, y: float, width: float, dir: str | None = None,
        initial: str | None = None, max_node_w: float | None = None, returns: str | None = None, straighten: bool | None = None, id: str | None = None,
    ) -> None:
        """lib/dsl/diagrams.ts's stateDiagram(): states (boxes) and transitions (arrows) that
        place themselves in layers, flowing left to right (dir: 'down' for top to bottom). A
        transition that goes back, skips a state or loops on itself is routed around the
        others. `states`: [{id, label, sub?, tone?, shape?, final?}]. `transitions`:
        [{from, to, label?, line?, tone?, strong?}]. A state's `icon` is NOT supported (see
        states.py's module docstring)."""
        band = states_band(states, transitions, dir=dir, initial=initial, max_node_w=max_node_w, returns=returns, straighten=straighten, id=id)
        self._elements.append(_States(x=x, y=y, w=width, band=band))

    def cause_tree(
        self, nodes: list[dict], links: list[dict], *, x: float, y: float, width: float, dir: str | None = None,
        max_node_w: float | str | None = None, core_driver: bool | None = None, role_tags: bool | dict | None = None,
        hop: bool | str | None = None, tree: str | None = None, layer: str | None = None, counts: bool | None = None,
        core_driver_label: str | None = None, returns: str | None = None, straighten: bool | None = None,
        fold: bool | None = None, id: str | None = None,
    ) -> None:
        """lib/dsl/diagrams.ts's causeTree(): entities and cause -> effect arrows that place
        themselves in layers, causes at the bottom and effects at the top by default. Current
        / Future Reality Tree, Prerequisite Tree and Transition Tree are all this figure: an
        arrow across an AND arc means "together", separate arrows mean "either". `nodes`:
        [{id, label, sub?, role?, tone?, core?, foldsInto?}]. `links`: [{from, to, line?,
        kind?, back?}] (`from` is an array for an AND). pdpc()/relationDiagram()/
        whyWhyTree()/transitionUnits() and the `mirrors`-tracking are NOT supported (see
        toc.py's module docstring)."""
        band = cause_band(
            nodes, links, dir=dir, max_node_w=max_node_w, core_driver=core_driver, role_tags=role_tags, hop=hop,
            tree=tree, layer=layer, counts=counts, core_driver_label=core_driver_label, returns=returns,
            straighten=straighten, fold=fold, id=id,
        )
        self._elements.append(_Cause(x=x, y=y, w=width, band=band))

    def flowchart(
        self, nodes: list[dict], edges: list[dict], *, x: float, y: float, width: float, dir: str | None = None,
        max_node_w: float | None = None, returns: str | None = None, straighten: bool | None = None, id: str | None = None,
    ) -> None:
        """lib/dsl/diagrams.ts's flowchart(): steps, decisions (a diamond that holds the
        question) and start/end pills, joined by arrows; Yes/No go on the arrows that leave
        a decision. Places itself like state_diagram() and runs down unless `dir` says
        otherwise; a return to an earlier node goes round the outside by default
        (`returns: 'outer'`). `nodes`: [{id, label?, sub?, kind? ('process'(default)/
        'decision'/'terminator'), tone?}]. `edges`: [{from, to, label?, line?, tone?,
        strong?}]."""
        band = flowchart_band(nodes, edges, dir=dir, max_node_w=max_node_w, returns=returns, straighten=straighten, id=id)
        self._elements.append(_States(x=x, y=y, w=width, band=band))
