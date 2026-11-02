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
import {renderBoxRect, renderConnect} from '../../lib/emit-boxes.ts';
import {escapeXml, escapeAttr, snap4, textLines, emojiSpan} from '../../lib/emit-common.ts';
import {toneEnv, runColorOf} from '../../lib/tokens.ts';
import {emitSvg} from '../../lib/emit.ts';

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
