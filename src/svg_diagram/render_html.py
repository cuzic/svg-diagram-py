"""The standalone HTML wrapper — spec section 7.

New, Python-only code: Node has no download-link HTML export to port from
(confirmed during planning — grepping the Node repo for `download=` found
nothing). This exists because, in the ChatGPT/Gemini/M365 Copilot Code
Interpreter sandboxes this whole port targets, a bare .svg download was
unreliable in testing while an HTML page with the SVG inlined worked
(see the conversation history this plan was written from) — so HTML, not
SVG, is the primary deliverable.
"""

from __future__ import annotations

import base64

from .emit_common import escape_xml


def render_html(svg: str, *, title: str = "SVG diagram", download_name: str = "diagram.svg") -> str:
    svg_b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape_xml(title)}</title>
</head>
<body>
{svg}
<p><a download="{escape_xml(download_name)}" href="data:image/svg+xml;base64,{svg_b64}">{escape_xml(download_name)} をダウンロード</a></p>
</body>
</html>
"""
