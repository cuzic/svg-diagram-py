// Golden-master CLI for the Python port's drawing-layer tests.
//
// This imports the *actual* Node.js svg-diagram emit functions directly (no
// build step — Node's native TS type-stripping runs this file as-is, same as
// the rest of the repo) and exposes them over a line-based JSON protocol so
// pytest can compare Python's output against Node's byte-for-byte.
//
// Scope: only the drawing-layer primitives the Python MVP ports (see
// /home/cuzic/.claude/plans/adaptive-popping-wadler.md). Layout/auto-position
// is NOT covered here — every input already carries its final x/y/w/h.
//
// Protocol: one JSON object per line on stdin, one JSON object per line on
// stdout (JSON Lines), so a single long-lived process can serve an entire
// pytest session instead of paying Node's ~0.5s module-load cost per case.
//   in:  {"kind": "box", "x":10, "y":20, "w":100, "h":50, "tone": "accent"}
//   out: {"ok": true, "result": "<rect .../>"}

import {createInterface} from 'node:readline';
import {renderBoxRect, renderConnect, renderStamp, renderTag, renderStepBadge, renderRaw, renderLegend, renderStatus} from '../../lib/emit-boxes.ts';
import {escapeXml, escapeAttr, snap4, textLines, emojiSpan, arrowPath} from '../../lib/emit-common.ts';
import {toneEnv, runColorOf} from '../../lib/tokens.ts';
import {emitSvg} from '../../lib/emit.ts';
import {splitAtoms} from '../../lib/atoms.ts';
import {wrapText} from '../../lib/wrap.ts';
import type {WrapMode} from '../../lib/wrap.ts';
import {badgeSvg, pillSvg} from '../../lib/badge.ts';
import {gridColumns, rowChildGeometry, gridChildGeometry, colSlots} from '../../lib/layout-util.ts';
import {layoutPeople, layoutDots} from '../../lib/people.ts';
import {renderPeople, renderDots} from '../../lib/emit-boxes.ts';
import {layoutTimeline} from '../../lib/timeline.ts';
import {renderTimeline, renderGantt} from '../../lib/emit-figures.ts';
import {layoutGantt} from '../../lib/gantt.ts';
import {layoutCloudBand} from '../../lib/toc.ts';
import {renderCloud} from '../../lib/emit-figures.ts';
import {layoutTree, layoutBalanced, layoutLayered, breakCycles} from '../../lib/graph-layout.ts';
import {layoutHanging, layoutBrace, layoutFishbone, layoutTimelineMap, mirror} from '../../lib/map-layouts.ts';
import {layoutTreeBand, measureNode, nodeRuns} from '../../lib/tree.ts';
import {renderTree} from '../../lib/emit-figures.ts';
import {layoutTable, layoutSequence} from '../../lib/seq-table.ts';
import {renderTable, renderSequence} from '../../lib/emit-tables.ts';
import {chevronBand, funnelBand, cycleBand, vennBand, concentricBand, emblemBand, valueChainBand, layoutFlowShape} from '../../lib/flow-shapes.ts';
import {renderFlowShape} from '../../lib/emit-figures.ts';
import {wordartBand, layoutWordArt} from '../../lib/wordart.ts';
import {renderWordArt} from '../../lib/emit-wordart.ts';
import {bars} from '../../lib/dsl/bars.ts';
import {layoutBars} from '../../lib/bars.ts';
import {renderBars} from '../../lib/emit-figures.ts';
import {bowtie, faultTree} from '../../lib/dsl/diagrams.ts';
import {layoutBowtie} from '../../lib/bowtie.ts';
import {renderBowtie} from '../../lib/emit-bowtie.ts';
import {layoutFta} from '../../lib/fta.ts';
import {renderFta} from '../../lib/emit-fta.ts';
import {heatmap, sankey, radar, treemap, waterfall, stackedBars, mekko, tornado, butterfly, harvey, bubble, combo} from '../../lib/dsl/charts.ts';
import {catplot, boxplot, violinplot, stripplot, swarmplot, pointplot, barplot, displot, histplot, kdeplot, ecdfplot, rugplot, hist2d, jointplot, kde2d as kde2dDsl, pairplot, regplot, residplot, clustermap} from '../../lib/dsl/charts-stats.ts';
import {quadrantBand, layoutQuadrant} from '../../lib/quadrant.ts';
import {renderQuadrant} from '../../lib/emit-figures.ts';
import {plane} from '../../lib/dsl/figures.ts';
import {lines, burndown, burnup, strategyCanvas} from '../../lib/dsl/charts.ts';
import {layoutPlane} from '../../lib/plane.ts';
import {renderPlane} from '../../lib/emit-figures.ts';
import {layoutChart} from '../../lib/charts.ts';
import {renderChart} from '../../lib/charts-emit.ts';
import {sum, meanOf, sdOf, quantile, boxStats, tCritical95, errorBar, kde, swarmOffsets, binCounts, binIndex, polyFit, kde2d, averageLinkage, dendrogramOrder, lowessFit} from '../../lib/stats.ts';
import type {Merge} from '../../lib/stats.ts';

// Maps-to-plain-object helper: Node's layout functions return a `Map`, which JSON.stringify
// serializes as `{}` (silently empty!) — convert to a plain object before returning so the
// CLI's JSON response actually carries the node positions.
function mapToObj<K extends string, V>(m: Map<K, V>): Record<string, V> {
  return Object.fromEntries(m);
}
function treeLayoutToPlain(t: {nodes: Map<string, unknown>; edges: unknown; w: number; h: number; braces?: unknown}) {
  return {nodes: mapToObj(t.nodes), edges: t.edges, w: t.w, h: t.h, ...(t.braces ? {braces: t.braces} : {})};
}
function layeredLayoutToPlain(t: {nodes: Map<string, unknown>; edges: unknown; layers: Map<string, number>; w: number; h: number; folded?: unknown}) {
  return {nodes: mapToObj(t.nodes), edges: t.edges, layers: mapToObj(t.layers), w: t.w, h: t.h, ...(t.folded ? {folded: t.folded} : {})};
}

// Shared dummy width function for layoutPeople/layoutDots golden tests, same technique as
// atoms.py/wrap.py: tests the ALGORITHM (icon grid geometry, dot pile packing), not real
// pixel text widths (those depend on each side's `size`/`label` text, measured here with a
// trivial stand-in so both sides agree without needing HarfBuzz).
const peopleWidthOf = (atom: string): number => [...atom].length * 8;

// Phase A's wrap/atoms golden tests inject the SAME trivial width function on both sides
// (codepoint count, ignoring size/weight/font) — see py/src/svg_diagram/wrap.py's module
// docstring and tests/test_wrap.py. This tests the SPLITTING/WRAPPING DECISIONS only;
// real pixel widths come from HarfBuzz on the Node side and are not golden-tested here.
const dummyWidthOf = (atom: string): number => [...atom].length;

const tones = toneEnv(undefined); // NO_TONES: tone overrides are out of MVP scope
const roles = {title: 15, label: 14, body: 14, note: 14, banner: 16, stat: 34, display: 56};

interface Req {
  kind: string;
  [key: string]: unknown;
}

function handle(req: Req): unknown {
  switch (req.kind) {
    case 'box':
      return renderBoxRect(
        {x: req.x as number, y: req.y as number, w: req.w as number, h: req.h as number, tone: req.tone as never, dashed: req.dashed as boolean | undefined, dim: req.dim as boolean | undefined, dataNode: req.dataNode as string | undefined},
        (req.day ?? 1) as never,
        tones,
        (req.defaultTone ?? 'plain') as never,
      );
    case 'connect':
      return renderConnect(
        {points: req.points, arrow: req.arrow ?? 'end', weight: req.weight, line: req.line, tone: req.tone, dim: req.dim, label: req.label, chipBox: req.chipBox} as never,
        (req.day ?? 1) as never,
        tones,
        roles,
      );
    case 'escapeXml':
      return escapeXml(req.text as string);
    case 'escapeAttr':
      return escapeAttr(req.text as string);
    case 'snap4':
      return snap4(req.n as number);
    case 'runColorOf':
      return runColorOf(tones, req.runTone as never, req.boxTone as never, (req.day ?? 1) as never);
    case 'splitAtoms':
      return splitAtoms(req.text as string);
    case 'wrapText':
      return wrapText(req.text as string, {maxWidth: req.maxWidth as number, atomWidth: dummyWidthOf, mode: (req.mode ?? 'char') as WrapMode});
    case 'badgeSvg':
      return badgeSvg({
        cx: req.cx as number, cy: req.cy as number, shape: req.shape as never, r: req.r as number, w: req.w as number,
        label: req.label as string, aria: req.aria as string, size: req.size as number, weight: req.weight as number | undefined,
        fill: req.fill as string, stroke: req.stroke as string | null | undefined, sw: req.sw as number | undefined, text: req.text as string | undefined,
        baseline: req.baseline as number | undefined, snap: snap4, esc: escapeXml,
      });
    case 'pillSvg':
      return pillSvg({
        x: req.x as number, y: req.y as number, w: req.w as number, h: req.h as number,
        fill: req.fill as string, stroke: req.stroke as string | null | undefined, sw: req.sw as number | undefined, dash: req.dash as string | undefined,
        cx: req.cx as number, baseline: req.baseline as number, text: req.textColor as string, size: req.size as number,
        weight: req.weight as number | undefined, labelHtml: req.labelHtml as string, rawY: req.rawY as number | undefined,
      });
    case 'gridColumns':
      return gridColumns(req.contentWidth as number, req.n as number, req.gap as number, {fixedGap: req.fixedGap as boolean | undefined, centerGutter: req.centerGutter as boolean | undefined, anyGap: req.anyGap as boolean | undefined});
    case 'rowChildGeometry':
      return rowChildGeometry(req.band as never, req.contentWidth as number);
    case 'gridChildGeometry':
      return gridChildGeometry(req.band as never, req.contentWidth as number);
    case 'colSlots':
      return colSlots(req.children as never);
    case 'renderStamp':
      return renderStamp({x: req.x as number, y: req.y as number, w: req.w as number, h: req.h as number, stamp: req.stamp as string | undefined, stampW: req.stampW as number | undefined}, roles);
    case 'renderTag':
      return renderTag({tagBox: {x: req.x as number, y: req.y as number, w: req.w as number, h: req.h as number}, tag: req.tag, tagTone: req.tagTone, tone: req.tone, dim: req.dim} as never, (req.day ?? 1) as never, tones, roles);
    case 'renderStepBadge': {
      // titleBaselineY = y + padY + lineY0 — computed the same way Node's renderStepBadge does
      // internally, so Python's render_step_badge (which takes title_baseline_y directly, since
      // computing wrapped-run baselines is layout, not drawing) can be golden-tested against this.
      const y = req.y as number, padY = req.padY as number, lineY0 = req.lineY0 as number;
      return renderStepBadge({x: req.x as number, y, padX: req.padX as number, padY, step: req.step, tone: req.tone, dim: req.dim, wrappedRuns: [{lineYs: [lineY0]}]} as never, (req.day ?? 1) as never);
    }
    case 'arrowPath':
      return arrowPath(req.points as never, req.color as string, req.line as never, (req.width ?? 2) as number, (req.headAt ?? 'end') as never, (req.end ?? 'arrow') as never);
    case 'renderLegend':
      return renderLegend({items: req.items as never} as never, (req.day ?? 1) as never, tones, roles);
    case 'layoutPeople': {
      const band = {cols: req.cols, size: req.size, gap: req.gap, side: req.side, total: req.total, count: req.count, count2: req.count2 ?? 0, align: req.align, tone: req.tone, tone2: req.tone2, rest: req.rest, alt: req.alt, id: undefined} as never;
      return layoutPeople(band, req.x as number, req.y as number, req.cw as number, peopleWidthOf, (req.day ?? 1) as never, roles);
    }
    case 'layoutDots': {
      const band = {width: req.width, r: req.r, dots: req.dots, zones: req.zones, min: req.min, max: req.max, lowLabel: req.lowLabel, highLabel: req.highLabel, height: req.height, alt: req.alt, id: undefined} as never;
      return layoutDots(band, req.x as number, req.y as number, req.cw as number, peopleWidthOf, (req.day ?? 1) as never, roles);
    }
    case 'renderPeople':
      return renderPeople({x: req.x, y: req.y, size: req.size, icons: req.icons, texts: req.texts, tone: req.tone, tone2: req.tone2, rest: req.rest, alt: req.alt} as never, (req.day ?? 1) as never, tones);
    case 'renderDots':
      return renderDots({axis: req.axis, zones: req.zones, dots: req.dots, texts: req.texts, r: req.r, alt: req.alt} as never, (req.day ?? 1) as never, tones);
    case 'layoutTimeline': {
      const band = {now: req.now, deadline: req.deadline, marks: req.marks ?? [], from: req.from, to: req.to, span: req.span, remaining: req.remaining, id: undefined, reveal: undefined, until: undefined} as never;
      return layoutTimeline(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles);
    }
    case 'renderTimeline':
      return renderTimeline(req.band as never, (req.day ?? 1) as never);
    case 'layoutGantt': {
      const band = {rows: req.rows, from: req.from, to: req.to, today: req.today, todayLabel: req.todayLabel, extendToToday: req.extendToToday ?? false, id: undefined, reveal: undefined, until: undefined} as never;
      return layoutGantt(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles);
    }
    case 'renderGantt':
      return renderGantt(req.band as never, (req.day ?? 1) as never);
    case 'layoutCloudBand': {
      const band = {a: req.a, b: req.b, c: req.c, d: req.d, d2: req.d2, maxNodeW: req.maxNodeW, assumptions: req.assumptions, conflictLabel: req.conflictLabel, id: undefined, reveal: undefined, until: undefined} as never;
      const env = {wrap: (req.wrap ?? 'phrase') as never, keepWords: false};
      return layoutCloudBand(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles, env);
    }
    case 'renderCloud':
      return renderCloud(req.band as never, (req.day ?? 1) as never, tones);
    case 'layoutTree':
      return treeLayoutToPlain(layoutTree(req.root as never, {dir: req.dir, gap: req.gap, levelGap: req.levelGap}));
    case 'layoutBalanced':
      return treeLayoutToPlain(layoutBalanced(req.root as never, {gap: req.gap, levelGap: req.levelGap, sides: req.sides}));
    case 'layoutLayered':
      return layeredLayoutToPlain(layoutLayered(req.nodes as never, req.edges as never, req.opts as never));
    case 'breakCycles':
      return [...breakCycles(req.nodes as never, req.edges as never, (req.declared ?? []) as never, (req.start ?? []) as never)].sort((a, b) => a - b);
    case 'layoutHanging':
      return treeLayoutToPlain(layoutHanging(req.root as never, {rowFirst: req.rowFirst, gap: req.gap, indent: req.indent, rowGap: req.rowGap}));
    case 'layoutBrace':
      return treeLayoutToPlain(layoutBrace(req.root as never, {gap: req.gap}));
    case 'layoutFishbone':
      return treeLayoutToPlain(layoutFishbone(req.root as never, {gap: req.gap}));
    case 'layoutTimelineMap':
      return treeLayoutToPlain(layoutTimelineMap(req.root as never, {gap: req.gap}));
    case 'mirror': {
      const l = req.layout as {nodes: Record<string, unknown>; edges: unknown; w: number; h: number; braces?: unknown};
      const layout = {...l, nodes: new Map(Object.entries(l.nodes))};
      return treeLayoutToPlain(mirror(layout as never, req.axis as never));
    }
    case 'measureNode':
      return measureNode(req.label as string, req.sub as string | undefined, req.maxW as number, peopleWidthOf, roles, (req.mode ?? 'phrase') as never, (req.floor ?? false) as boolean, {keepWordsCap: req.keepWordsCap, keepWords: req.keepWords});
    case 'nodeRuns':
      return nodeRuns(req.r as never, req.l as never, roles);
    case 'layoutTreeBand': {
      const band = {type: 'tree', root: req.root, dir: req.dir, maxNodeW: req.maxNodeW, balanced: req.balanced, layout: req.layoutMode, sides: req.sides, edges: req.edgesOpt, id: undefined, reveal: undefined, until: undefined} as never;
      const env = {wrap: (req.wrap ?? 'phrase') as never, keepWords: false};
      return layoutTreeBand(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles, env);
    }
    case 'renderTree':
      return renderTree(req.band as never, (req.day ?? 1) as never, tones);
    case 'layoutTable': {
      const band = {
        type: 'table', columns: req.columns, rows: req.rows, width: req.width, title: req.title, dense: req.dense,
        header: req.header, rowHeader: req.rowHeader, headerH: req.headerH, cellH: req.cellH, rowCurve: req.rowCurve,
        tone: req.tone, id: undefined, reveal: undefined, until: undefined,
      } as never;
      return layoutTable(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles, (req.wrap ?? 'phrase') as never);
    }
    case 'renderTable':
      return renderTable(req.band as never, (req.day ?? 1) as never, tones, roles);
    case 'layoutSequence': {
      const band = {type: 'sequence', actors: req.actors, steps: req.steps, numbered: req.numbered, id: undefined, reveal: undefined, until: undefined} as never;
      return layoutSequence(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles, (req.wrap ?? 'phrase') as never);
    }
    case 'renderSequence':
      return renderSequence(req.band as never, (req.day ?? 1) as never, tones, roles);
    case 'layoutFlowShape': {
      let band: never;
      const o = req.opts ?? {};
      if (req.shape === 'chevron') band = chevronBand(req.items as never, o) as never;
      else if (req.shape === 'funnel') band = funnelBand(req.items as never, o) as never;
      else if (req.shape === 'cycle') band = cycleBand(req.items as never, o) as never;
      else if (req.shape === 'venn') band = vennBand(req.items as never, o) as never;
      else if (req.shape === 'concentric') band = concentricBand(req.items as never, o) as never;
      else if (req.shape === 'emblem') band = emblemBand(req.items as never, o) as never;
      else if (req.shape === 'valueChain') band = valueChainBand(req.items as never, o) as never; // req.items = {support?, primary} for this one shape
      else throw new Error(`unknown flow shape: ${req.shape}`);
      return layoutFlowShape(band, req.x as number, req.y as number, req.cw as number, peopleWidthOf, roles, (req.wrap ?? 'phrase') as never);
    }
    case 'renderFlowShape':
      return renderFlowShape(req.band as never, (req.day ?? 1) as never, tones);
    case 'layoutWordArt': {
      const band = wordartBand(req.text as string, (req.opts ?? {}) as never);
      return layoutWordArt(band, req.x as number, req.y as number, req.cw as number, peopleWidthOf, roles, (req.wrap ?? 'phrase') as never);
    }
    case 'renderWordArt':
      return renderWordArt(req.band as never, (req.day ?? 1) as never, (req.dim ?? false) as never);
    case 'layoutBars': {
      const band = bars(req.data as never, (req.opts ?? {}) as never);
      return layoutBars(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles);
    }
    case 'renderBars':
      return renderBars(req.band as never, (req.day ?? 1) as never);
    case 'layoutChart': {
      let band: never;
      if (req.chartKind === 'heatmap') band = heatmap(req.rows as never, req.cols as never, req.values as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'sankey') band = sankey(req.nodes as never, req.links as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'radar') band = radar(req.axes as never, req.series as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'treemap') band = treemap(req.tree as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'waterfall') band = waterfall(req.steps as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'stackedBars') band = stackedBars(req.columns as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'mekko') band = mekko(req.columns as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'tornado') band = tornado(req.items as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'butterfly') band = butterfly(req.rows as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'harvey') band = harvey(req.rows as never, req.cols as never, req.values as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'bubble') band = bubble(req.points as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'combo') band = combo(req.categories as never, req.series as never, (req.opts ?? {}) as never) as never;
      else if (req.chartKind === 'catplot') {
        const catFns: Record<string, (data: never, opts: never) => never> = {catplot, boxplot, violinplot, stripplot, swarmplot, pointplot, barplot} as never;
        const fn = catFns[req.catFn as string];
        if (!fn) throw new Error(`unknown catFn: ${req.catFn}`);
        band = fn(req.data as never, (req.opts ?? {}) as never);
      }
      else if (req.chartKind === 'distplot') {
        const distFns: Record<string, (data: never, opts: never) => never> = {displot, histplot, kdeplot, ecdfplot, rugplot} as never;
        const fn = distFns[req.distFn as string];
        if (!fn) throw new Error(`unknown distFn: ${req.distFn}`);
        band = fn(req.data as never, (req.opts ?? {}) as never);
      }
      else if (req.chartKind === 'multiplot') {
        const multiFns: Record<string, (data: never, opts: never) => never> = {hist2d, jointplot, kde2d: kde2dDsl, pairplot} as never;
        const fn = multiFns[req.multiFn as string];
        if (!fn) throw new Error(`unknown multiFn: ${req.multiFn}`);
        band = fn(req.data as never, (req.opts ?? {}) as never);
      }
      else if (req.chartKind === 'regplot') {
        const regFns: Record<string, (data: never, opts: never) => never> = {regplot, residplot} as never;
        const fn = regFns[req.regFn as string];
        if (!fn) throw new Error(`unknown regFn: ${req.regFn}`);
        band = fn(req.data as never, (req.opts ?? {}) as never);
      }
      else if (req.chartKind === 'clustermap') band = clustermap(req.rows as never, req.cols as never, req.values as never, (req.opts ?? {}) as never) as never;
      else throw new Error(`unknown chart kind: ${req.chartKind}`);
      return layoutChart(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles, (req.wrap ?? 'phrase') as never);
    }
    case 'renderChart':
      return renderChart(req.band as never, (req.day ?? 1) as never, emojiSpan);
    case 'layoutPlane': {
      const band = plane(req.opts as never);
      return layoutPlane(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles);
    }
    case 'renderPlane':
      return renderPlane(req.band as never, (req.day ?? 1) as never, tones);
    case 'layoutQuadrant': {
      const band = quadrantBand(req.opts as never);
      return layoutQuadrant(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles, (req.wrap ?? 'phrase') as never);
    }
    case 'renderQuadrant':
      return renderQuadrant(req.band as never, (req.day ?? 1) as never, tones);
    case 'layoutBowtie': {
      const band = bowtie(req.input as never, (req.opts ?? {}) as never);
      const env = {wrap: (req.wrap ?? 'phrase') as never, keepWords: false};
      return layoutBowtie(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles, env);
    }
    case 'renderBowtie':
      return renderBowtie(req.band as never, (req.day ?? 1) as never, tones);
    case 'layoutFta': {
      const band = faultTree(req.root as never, (req.opts ?? {}) as never);
      const env = {wrap: (req.wrap ?? 'phrase') as never, keepWords: false, space: (req.space ?? 1) as number};
      return layoutFta(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles, env);
    }
    case 'renderFta':
      return renderFta(req.band as never, (req.day ?? 1) as never, tones);
    case 'layoutLines': {
      let band: never;
      if (req.linesKind === 'lines') band = lines(req.series as never, (req.opts ?? {}) as never) as never;
      else if (req.linesKind === 'burndown') band = burndown(req.spec as never, (req.opts ?? {}) as never) as never;
      else if (req.linesKind === 'burnup') band = burnup(req.spec as never, (req.opts ?? {}) as never) as never;
      else if (req.linesKind === 'strategyCanvas') band = strategyCanvas(req.factors as never, req.series as never, (req.opts ?? {}) as never) as never;
      else throw new Error(`unknown lines kind: ${req.linesKind}`);
      return layoutPlane(band, req.x as number, req.y as number, req.w as number, peopleWidthOf, roles);
    }
    case 'renderStatus':
      return renderStatus({pill: {x: req.x as number, y: req.y as number, w: req.w as number, h: req.h as number}, textY: req.textY as number, text: req.text as string, status: req.status as string, size: (req.size ?? 14) as number} as never);
    case 'renderRaw':
      return renderRaw({x: req.x as number, y: req.y as number, w: req.w as number, h: req.h as number, draw: (ctx: {color: (t: string) => string}) => `<circle cx="50" cy="50" r="10" fill="${ctx.color(req.tone as string)}"/>`} as never, (req.day ?? 1) as never);
    case 'emojiSpan':
      return emojiSpan(req.text as string);
    case 'textLines':
      return textLines(req.lines as string[], {x: req.x as number, top: req.top as number, size: req.size as number, weight: req.weight as number | undefined, anchor: req.anchor as never, fill: req.fill as string, mono: req.mono as boolean | undefined});
    case 'emitSvgFixture':
      // Used once, offline, to (re)capture golden/fixtures/*.json — not called by pytest itself.
      return emitSvg(req.diagram as never);
    case 'stats': {
      const fn = req.fn as string, a = (req.args ?? []) as unknown[];
      const probeX = req.probeX as number[] | undefined;
      switch (fn) {
        case 'sum': return sum(a[0] as number[]);
        case 'meanOf': return meanOf(a[0] as number[]);
        case 'sdOf': return sdOf(a[0] as number[]);
        case 'quantile': return quantile(a[0] as number[], a[1] as number);
        case 'boxStats': return boxStats(a[0] as number[]);
        case 'tCritical95': return tCritical95(a[0] as number);
        case 'errorBar': return errorBar(a[0] as number[], a[1] as never) ?? null;
        case 'kde': return kde(a[0] as number[], a[1] as number[], a[2] as number | undefined);
        case 'swarmOffsets': return swarmOffsets(a[0] as number[], a[1] as number, a[2] as number) ?? null;
        case 'binCounts': return binCounts(a[0] as number[], a[1] as number[]);
        case 'binIndex': return binIndex(a[0] as number, a[1] as number[]);
        case 'polyFit': {
          const r = polyFit(a[0] as number[], a[1] as number[], a[2] as number);
          return {order: r.order, coef: r.coef, r2: r.r2, n: r.n, rss: r.rss, atValues: (probeX ?? []).map(r.at), halfValues: r.half ? (probeX ?? []).map(r.half) : null};
        }
        case 'kde2d': return kde2d(a[0] as number[], a[1] as number[], a[2] as number[], a[3] as number[]);
        case 'averageLinkage': return averageLinkage(a[0] as number[][]);
        case 'dendrogramOrder': return dendrogramOrder(a[0] as Merge[], a[1] as number);
        case 'lowessFit': {
          const f = lowessFit(a[0] as number[], a[1] as number[], a[2] as number | undefined, a[3] as number | undefined);
          return (probeX ?? []).map(f);
        }
        default: throw new Error(`unknown stats fn: ${fn}`);
      }
    }
    default:
      throw new Error(`unknown kind: ${req.kind}`);
  }
}

const rl = createInterface({input: process.stdin});
rl.on('line', (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;
  let out: string;
  try {
    const req = JSON.parse(trimmed) as Req;
    out = JSON.stringify({ok: true, result: handle(req)});
  } catch (e) {
    out = JSON.stringify({ok: false, error: e instanceof Error ? e.message : String(e)});
  }
  process.stdout.write(out + '\n');
});
