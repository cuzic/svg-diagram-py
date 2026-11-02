"""1:1 port of lib/tokens.ts — only the pieces the MVP drawing layer needs.

Golden master: lib/tokens.ts (Node.js, svg-diagram). Tone overrides
(``diagram({tones: {...}})``) are out of MVP scope: every lookup here behaves
as if Node's ``NO_TONES`` (no overrides) were in effect.
"""

from __future__ import annotations

from dataclasses import dataclass

# lib/tokens.ts:13-26
PALETTE: dict = {
    "bg": "#ffffff",
    "text": "#22201b",
    "muted": "#6f6659",
    "border": "#e0d6c5",
    "code": "#f6f8fa",
    "danger": "#b91c1c",
    1: {"accent": "#a8632b", "soft": "#f1e3d3"},
    2: {"accent": "#1f6e73", "soft": "#dbeeee"},
    "blue": {"accent": "#1d5fa8", "soft": "#dce9f7"},
    "teal": {"accent": "#1f6e73", "soft": "#dbeeee"},
    "amber": {"accent": "#a8632b", "soft": "#f1e3d3"},
}


@dataclass(frozen=True)
class ToneStyle:
    """lib/tokens.ts:95-112 (ToneStyle interface)."""

    fill: str
    stroke: str | None
    text: str
    ink: str
    dashed: bool
    as_text: bool
    slide_stroke: str | None = None
    chip_stroke: str | None = None


# lib/tokens.ts:113-123
TONES: dict[str, ToneStyle] = {
    "plain": ToneStyle(fill="bg", stroke="text", chip_stroke="muted", text="text", ink="text", dashed=False, as_text=False),
    "accent": ToneStyle(fill="soft", stroke="accent", text="accent", ink="accent", dashed=False, as_text=True),
    "new": ToneStyle(fill="soft", stroke="accent", text="text", ink="accent", dashed=False, as_text=False),
    "changed": ToneStyle(fill="bg", stroke="accent", text="text", ink="accent", dashed=False, as_text=False),
    "removed": ToneStyle(fill="code", stroke="muted", text="muted", ink="muted", dashed=True, as_text=False),
    "muted": ToneStyle(fill="code", stroke="muted", slide_stroke="border", chip_stroke="border", text="muted", ink="muted", dashed=False, as_text=True),
    "danger": ToneStyle(fill="bg", stroke="danger", text="danger", ink="danger", dashed=True, as_text=True),
    "solid": ToneStyle(fill="accent", stroke=None, text="bg", ink="accent", dashed=False, as_text=False),
    "solid-danger": ToneStyle(fill="danger", stroke=None, text="bg", ink="danger", dashed=False, as_text=False),
}

# lib/tokens.ts:125
TONE_ALIAS: dict[str, str] = {"ok": "accent", "warn": "danger", "off": "muted"}


def tone_style(tone: str | None) -> ToneStyle:
    """lib/tokens.ts:127-130 toneStyle(), with the ToneEnv fixed to NO_TONES."""
    name = "plain" if tone is None else TONE_ALIAS.get(tone, tone)
    return TONES.get(name, TONES["plain"])


def color_of(key: str, day: int | str) -> str:
    """lib/tokens.ts:224-227 colorOf()."""
    if key.startswith("#"):
        return key
    if key in ("accent", "soft"):
        return PALETTE[day][key]
    return PALETTE[key]


def text_key_of(tone: str | None) -> str:
    """lib/tokens.ts:216 textKeyOf(), NO_TONES fixed."""
    t = tone_style(tone)
    return t.ink if t.as_text else "text"


def text_color_of(tone: str | None, day: int | str) -> str:
    """lib/tokens.ts:229 textColorOf()."""
    return color_of(text_key_of(tone), day)


def is_solid_tone(tone: str | None) -> bool:
    """lib/tokens.ts:218 isSolidTone()."""
    return tone in ("solid", "solid-danger")


def run_color_of(run_tone: str | None, box_tone: str | None, day: int | str) -> str:
    """lib/tokens.ts:220-222 runColorOf(), NO_TONES fixed: the color of a box's text run — white on a
    solid-filled box (unless the run itself overrides the color), else the plain/tone text color."""
    if is_solid_tone(box_tone) and run_tone is None:
        return color_of(tone_style(box_tone).text, day)
    return text_color_of(run_tone, day)


def resolve_box_style(tone: str | None, day: int | str, dashed_override: bool | None = None) -> dict:
    """lib/emit-common.ts:45-50 resolveBoxStyle(), NO_TONES fixed."""
    t = tone_style(tone)
    stroke_key = t.stroke if isinstance(day, str) else (t.slide_stroke or t.stroke)
    fill = color_of(t.fill, day)
    stroke = color_of(stroke_key if stroke_key is not None else t.fill, day)
    dashed = t.dashed if dashed_override is None else dashed_override
    return {"fill": fill, "stroke": stroke, "dashed": dashed}


# lib/tokens.ts:245-249
FONT_STACKS: dict[str, str] = {
    "sans": "'Hiragino Sans','Hiragino Kaku Gothic ProN','Yu Gothic','YuGothic',Meiryo,'Noto Sans JP',sans-serif",
    "mono": "'JetBrains Mono','SF Mono','Menlo','Consolas','Liberation Mono','Courier New',monospace",
    "emoji": "'Noto Color Emoji','Segoe UI Emoji',sans-serif",
}

# lib/tokens.ts:269-271, 306
ROLES: dict[str, int] = {"title": 15, "label": 14, "body": 14, "note": 14, "banner": 16, "stat": 34, "display": 56}
CONNECT_LABEL_SIZE = 14
STRONG_STROKE = 5
TAG_SIZE = 14

# lib/tokens.ts:314-319 CELL_MARKS
CELL_MARKS: dict[str, dict] = {
    "ok": {"glyph": "○", "tone": "accent", "bold": False},
    "mid": {"glyph": "△", "tone": "text", "bold": False},
    "ng": {"glyph": "×", "tone": "danger", "bold": False},
    "best": {"glyph": "◎", "tone": "accent", "bold": True},
}


def relative_luminance(hex_color: str) -> float:
    """lib/tokens.ts:367-371 relativeLuminance()."""

    def lin(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def wcag_ratio(a: str, b: str) -> float:
    """lib/tokens.ts:372-375 wcagRatio()."""
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# lib/tokens.ts:326 SHADES
SHADES: list[float] = [1.0, 0.8, 0.65, 0.5, 0.35, 0.15]


def luminance(hex_color: str) -> float:
    """lib/tokens.ts:339-344 luminance() — ITU-R BT.601 perceptual-ish luminance."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def blend_luminance(base_hex: str, overlay_hex: str, alpha: float) -> float:
    """lib/tokens.ts:351-353 blendLuminance()."""
    return luminance(base_hex) * (1 - alpha) + luminance(overlay_hex) * alpha


def best_text_color(bg_luminance: float, paint=lambda h: h) -> str:
    """lib/tokens.ts:358-363 bestTextColor()."""
    white_delta = abs(luminance(paint("#ffffff")) - bg_luminance)
    text_delta = abs(luminance(paint(PALETTE["text"])) - bg_luminance)
    return "#ffffff" if white_delta >= text_delta else PALETTE["text"]
