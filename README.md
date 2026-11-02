# svg-diagram (Python port)

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
- 自動レイアウト・交差削減・100以上の専用図種(flowchart / bpmn / charts /
  wardley 等)は対象外。ただし **row()/grid() の子要素の幅配分アルゴリズムは
  「テキスト計測不要の純粋算術」なのでNode.jsとバイト同一に移植済み**
  (`layout_util.py`)。
- **box() の表現力拡張**(tag/stamp/step badge/frame:false/raw())、
  **caption()/group()/banner()**、**legend()**(swatch/line/AND/back/blocks、
  FTA・hex色・strong/doubleは対象外)を追加(2026-11-02)。
- **テキスト折返し判定アルゴリズム**(`lib/atoms.ts`/`lib/wrap.ts`、禁則処理・
  孤立文字救済・括弧の持ち上げ含む)はNode.jsと**同じダミー幅関数を注入して
  golden比較**し、分割・改行判定ロジック自体はバイト同一であることを確認済み
  (`atoms.py`/`wrap.py`)。ただし本番用の実際のピクセル幅(`approx_width.py`)
  はNode.jsの実際のHarfBuzz計測とは一致しない近似値 ——
  Python標準ライブラリのみで動かす(Geminiの「独自ライブラリインストール
  不可」制約への対応)ことを優先した意図的なトレードオフ。
- 次段階として cause()(TOCのCRT/FRT)・cloud()(対立解消図)・mindmap()/
  tree() を「配置も含めて同じロジックで移植」する作業が計画されている
  (規模・リスクが大きく異なるため cloud → mindmap → cause の順で、
  cause は別の計画として起票予定)。

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
| `src/svg_diagram/badge.py` | `lib/badge.ts` |
| `src/svg_diagram/legend.py` | `lib/emit-boxes.ts`の`renderLegend`(主要分岐のみ) |
| `src/svg_diagram/layout_util.py` | `lib/layout-util.ts`(定数+row/gridの幅配分算術) |
| `src/svg_diagram/atoms.py` | `lib/atoms.ts` |
| `src/svg_diagram/wrap.py` | `lib/wrap.ts` |
| `src/svg_diagram/approx_width.py` | なし(新規、`lib/measure.ts`等の近似代替) |
| `src/svg_diagram/model.py` | なし(新規) |
| `src/svg_diagram/render_html.py` | なし(新規) |

## 対応していないもの(現時点)

- `box({icon})`: アイコングリフは `svg-diagram.icons.json` というプロジェクト
  固有の設定ファイルから読む仕組み(Node.js自身もアイコンデータを同梱していない)
  なので、今回は見送った。
- `connect()`の`weight: 'strong'`・`line: 'double'`、`legend()`のFTA/hex色
  swatch・strong/double。
- cause()/cloud()/mindmap()/tree() 本体(次段階で着手予定)。
