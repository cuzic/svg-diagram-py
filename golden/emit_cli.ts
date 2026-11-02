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
