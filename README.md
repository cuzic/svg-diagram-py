# svg-diagram (Python port)

svg-diagram を、Python しか実行できないAIサンドボックス(ChatGPT Code
Interpreter / Gemini code execution / Microsoft 365 Copilot Code
Interpreter)から使えるようにするための移植。

[svg-diagram](https://github.com/cuzic/svg-diagram)(TypeScript版、本家)の
モノレポ内で開発され、Python移植だけを独立リポジトリとして切り出したもの。
band(図種)ごとの移植状況は [BANDS.md](BANDS.md) を参照。

## スコープ

- **配置(レイアウト)はこのPython版だけの新規実装**: `Diagram.box(x=, y=,
  width=, height=)` / `.arrow(start, end)` という絶対座標API。Node.js版の
  `box()`/`connect()` は常にフルの自動レイアウトパイプラインを通るため、
  これに対応するものはない。
- **描画スタイル(色・線幅・角丸・矢印・フォント宣言・エスケープ)は
  Node.js版からバイト同一で移植**し、`tests/test_golden_*.py` で
  Node.js実行結果と文字列完全一致を検証する(このリポジトリには比較対象の
  Node.jsソースが無いため、録音済みの期待値を `golden/fixtures/` から読む。
  由来と再生成手順は [golden/README.md](golden/README.md) を参照)。
- レイアウト(自動配置・交差削減)も、ボックス座標が確定していれば呼べる
  範囲(tree/mindmap/states/classes/pert/causalLoop/cause等の layered
  routing 系、swimlane()、wireframe()/screens())は移植済み。facet() は、
  Node側が共有する副作用ありの合成レイアウトエンジン(`LayoutCtx`)に
  依存しており、本移植の絶対座標APIとはアーキテクチャが不一致のため
  対象外([BANDS.md](BANDS.md)に判断根拠)。
- **`Diagram(width, height="auto")`**(この移植だけの新規機能、Node側に
  対応する機能はない): キャンバスの高さを、全要素の内容から自動で決める。
  box()/row()/grid()の絶対座標APIにはそもそも自動レイアウトのパイプ
  ラインが無いため、高さを手で決める以外の方法がなかった(2026-11)。
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

## 開発

```sh
uv run pytest        # 全テスト(golden比較 + Python単体テスト、Node.js不要)
uv run python -c "from svg_diagram import Diagram; ..."
```

golden テストは Node.js を起動せず、`golden/fixtures/` に録音済みの
期待値と比較する(詳細は [golden/README.md](golden/README.md))。

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
  なので見送った。
- `connect()`の`weight: 'strong'`・`line: 'double'`、`legend()`のFTA/hex色
  swatch・strong/double。swimlane()のステップを他bandからconnect()で
  参照する機能(`opts.flows`・`opts.laneOrder`)も同じ理由(共有アンカー
  レジストリが前提)で対象外。
- `facet()`: Node側が box()/row()/group()等と状態を共有する合成レイアウト
  エンジン(`LayoutCtx`)に依存しており、本移植の絶対座標APIとはアーキ
  テクチャが不一致のため対象外。
- `wireframe()`/`screens()`は本体(col/row/card + 20種類のウィジェット、
  dialog/toast、state matrix)を移植済みだが、`wireframe-parts.ts`
  (states/fusion/compare/region/robot/battery/signal/insight/breadcrumb/
  toggle/checkbox/radio/slider——監視・ロボット運用ダッシュボード向けの
  専用拡張)は対象外。
- `math()`(TeX組版、MathJax依存)・`image()`: 優先度低、または
  stdlib-onlyの方針と衝突するため見送り。

詳細な理由と、他の40以上のband(図種)それぞれの移植状況は
[BANDS.md](BANDS.md) を参照。
