# svg-diagram (Python port, MVP)

svg-diagram を、Python しか実行できないAIサンドボックス(ChatGPT Code
Interpreter / Gemini code execution / Microsoft 365 Copilot Code
Interpreter)から使えるようにするための移植。詳細な設計根拠は
`/home/cuzic/.claude/plans/adaptive-popping-wadler.md` を参照。

## スコープ

- **配置(レイアウト)はこのPython版だけの新規実装**: `Diagram.box(x=, y=,
  width=, height=)` / `.arrow(start, end)` という絶対座標API。Node.js版の
  `box()`/`connect()` は常にフルの自動レイアウトパイプラインを通るため、
  これに対応するものはない。
- **描画スタイル(色・線幅・角丸・矢印・フォント宣言・エスケープ)は
  Node.js版からバイト同一で移植**し、`tests/test_golden_*.py` で
  `golden/emit_cli.ts` 経由のNode.js実行結果と文字列完全一致を検証する。
- 自動レイアウト・テキスト自動折返し・交差削減・100以上の専用図種(flowchart
  / bpmn / charts / wardley 等)は対象外。

## 開発

```sh
uv run pytest        # 全テスト(golden比較 + Python単体テスト)
uv run python -c "from svg_diagram import Diagram; ..."
```

`tests/` の golden テストは Node.js(>=22.18、型ストリッピング必須)を
`golden/emit_cli.ts` 経由でサブプロセス実行する。Node非依存のテストだけ
走らせたい場合は `uv run pytest -k "not golden and not run_color_of"`。

## ファイル対応

| このファイル | Node.js側のゴールデンマスター |
| --- | --- |
| `src/svg_diagram/tokens.py` | `lib/tokens.ts` |
| `src/svg_diagram/emit_common.py` | `lib/emit-common.ts` |
| `src/svg_diagram/emit_boxes.py` | `lib/emit-boxes.ts` |
| `src/svg_diagram/emit.py` | `lib/emit.ts`(`emitSvgWith`、非export) |
| `src/svg_diagram/model.py` | なし(新規) |
| `src/svg_diagram/render_html.py` | なし(新規) |
